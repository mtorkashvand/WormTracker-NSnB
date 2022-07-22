#! python
#
# Copyright 2021
# Authors: Mahdi Torkashvand

"""
This creates a device for the auto tracker

Usage:
    tracker.py                   [options]

Options:
    -h --help                           Show this help.
    --commands_in=HOST:PORT             Host and Port for the incomming commands.
                                            [default: localhost:5001]
    --commands_out=HOST:PORT            Host and Port for the outgoing commands.
                                            [default: localhost:5000]
    --data_in=HOST:PORT                 Host and Port for the incomming image.
                                            [default: localhost:5005]
    --data_out=HOST:PORT                Host and Port for the incomming image.
                                            [default: localhost:5005]
    --format=UINT8_YX_512_512        Size and type of image being sent.
                                            [default: UINT8_YX_512_512]
"""

import pstats
import time
import json
from typing import Tuple

import zmq
import cv2
import numpy as np
from docopt import docopt

from wormtracker_scope.zmq.array import TimestampedSubscriber, TimestampedPublisher
from wormtracker_scope.zmq.publisher import Publisher
from wormtracker_scope.zmq.subscriber import ObjectSubscriber
from wormtracker_scope.zmq.utils import parse_host_and_port
from wormtracker_scope.devices.utils import array_props_from_string



class TrackerDevice():
    """This creates a device that subscribes to images from a camera
    and sends commands to the motors"""

    def __init__(
            self,
            commands_in: Tuple[str, int, bool],
            commands_out: Tuple[str, int],
            data_in: Tuple[str, int, bool],
            data_out: Tuple[str, int],
            fmt: str,
            name="tracker"):

        np.seterr(divide = 'ignore')
        self.status = {}
        self.data_out = data_out
        self.data_in = data_in
        self.poller = zmq.Poller()
        self.name = name
        (self.dtype, _, self.shape) = array_props_from_string(fmt)
        self.out = np.zeros(self.shape, dtype=self.dtype)

        self.data = np.zeros(self.shape)
        self.crop_size = self.shape[0] / 3
        self.crop_size_flag = False
        self.mean_sharpness = 0
        # self.max_sharpness = 0
        self.sharpness = 0
        self.threshold = 30
        self.counter = 0
        self.vz = 16
        self.deltax = 0
        self.deltay = 0
        self.bbox = [0, 0, self.shape[0], self.shape[1]]
        self.tracking = 0

        self.ds_shape = self.data[::4, ::4].shape

        self.running = 1

        self.command_publisher = Publisher(
            host=commands_out[0],
            port=commands_out[1],
            bound=commands_out[2])
        
        self.data_publisher = TimestampedPublisher(
            host=self.data_out[0],
            port=self.data_out[1],
            bound=self.data_out[2],
            shape=self.shape,
            datatype=self.dtype)

        self.command_subscriber = ObjectSubscriber(
            obj=self,
            name=name,
            host=commands_in[0],
            port=commands_in[1],
            bound=commands_in[2])

        self.data_subscriber = TimestampedSubscriber(
            host=self.data_in[0],
            port=self.data_in[1],
            bound=self.data_in[2],
            shape=self.shape,
            datatype=self.dtype)

        self.poller.register(self.command_subscriber.socket, zmq.POLLIN)
        self.poller.register(self.data_subscriber.socket, zmq.POLLIN)

        time.sleep(1)
        self.publish_status()

        self.mask = self.get_mask(self.data[::4, ::4].shape[0])

    def get_mask(self, radius):

        r = np.linspace(int((1-radius) / 2),
                        int((1+radius) / 2), radius)

        Y, X = np.meshgrid(r, r, indexing='ij')
        
        g = np.exp(-(Y**4)/(2.0 * radius**4)
                   -(X**4)/(2.0 * radius**4))

        return g / np.max(g)


    def process(self):
        """This processes the incoming images and sends move commands to zaber."""
        msg = self.data_subscriber.get_last()

        if msg is not None:
            self.data = msg[1]


        # t0 = time.time()
        dsimg = np.invert(self.data[::4, ::4])
        dsimg = cv2.medianBlur(dsimg, 3)
        dsimg = np.multiply(dsimg, self.mask)
        dsimg = dsimg.astype(np.float16) / max(dsimg.max(), 1)
        dsimg = (dsimg ** 4 * 255).astype(np.uint8)
        dsimg[dsimg<self.threshold]=0
        contours, _ = cv2.findContours(dsimg, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        if len(contours) >= 1:
            max_size_idx = np.argmax([contour.shape[0] for contour in contours])
            self.bbox = cv2.boundingRect(contours[max_size_idx])
            self.bbox = [4 * i for i in self.bbox]


        self.Dx= self.bbox[0] + self.bbox[2] // 2 - self.shape[1] // 2
        self.Dy = self.bbox[1] + self.bbox[3] // 2 - self.shape[0] // 2
        self.vx = np.sign(self.Dx) * int(((np.abs(self.Dx) * 2 / self.shape[1]) ** 0.7) * self.shape[1] / 2)
        self.vy = np.sign(self.Dy) * int(((np.abs(self.Dy) * 2 / self.shape[0]) ** 0.7) * self.shape[0] / 2)
        p1 = (self.bbox[0], self.bbox[1])
        p2 = (self.bbox[0] + self.bbox[2], self.bbox[1] + self.bbox[3])



        

        center = [self.bbox[0] + self.bbox[2] // 2, self.bbox[1] + self.bbox[3] // 2]
        x_range = [max(0, center[0] - self.crop_size // 2), min(self.shape[0]-1, center[0] + self.crop_size // 2)]
        y_range = [max(0, center[1] - self.crop_size // 2), min(self.shape[1]-1, center[1] + self.crop_size // 2)]

        cropped_img = self.data[int(y_range[0]):int(y_range[1]), int(x_range[0]):int(x_range[1])]

        try:
            sharpness = self.calculate_sharpness(cropped_img)
        except:
            sharpness = 0
        
        self.mean_sharpness += (sharpness / 10)

        if self.counter % 5 == 0:
            delta = self.mean_sharpness - self.sharpness
            if delta < 0:
                self.vz = -self.vz
            self.sharpness = self.mean_sharpness
            self.mean_sharpness = 0


        # print(time.time() - t0)

        annotated_img = self.data.copy()
        cv2.rectangle(annotated_img, p1, p2, (0, 0, 0), 2, 1)

        self.data_publisher.send(annotated_img)
        if self.tracking:
            if not self.crop_size_flag:
                self.crop_size = max(self.bbox[2], self.bbox[3]) // 2
                self.crop_size_flag=True
            
            self.command_publisher.send("teensy_commands movey {}".format(-self.vy))
            self.command_publisher.send("teensy_commands movex {}".format(-self.vx))
            self.command_publisher.send("teensy_commands movez {}".format(self.vz))
        
        self.counter += 1


    def calculate_sharpness(self, img, size=10):
        (h, w) = img.shape
        (cX, cY) = (int(w / 2), int(h / 2))
        fft = np.fft.fft2(img)
        fftShift = np.fft.fftshift(fft)
        fftShift[cY - size:cY + size, cX - size:cX + size] = 0
        fftShift = np.fft.ifftshift(fftShift)
        recon = np.fft.ifft2(fftShift)
        magnitude = 20 * np.log(np.abs(recon))
        return np.mean(magnitude)
        



    def change_threshold(self, direction):
        self.threshold = np.clip(self.threshold + direction, 0, 255)

        print("Threshold: {}".format(self.threshold))

    
    def toggle_tracking(self):
        if self.tracking:
            print("tracking stopped")
            self.command_publisher.send("teensy_commands movey 0")
            self.command_publisher.send("teensy_commands movex 0")
            self.command_publisher.send("teensy_commands movez 0")
            self.tracking = 0
            self.crop_size_flag = False
        else:
            self.tracking = 1
            print("tracking started")


    def set_shape(self, y ,x):
        self.poller.unregister(self.data_subscriber.socket)

        self.shape = (y, x)
        self.tracker.set_shape(y, x)
        self.out = np.zeros(self.shape, dtype=self.dtype)

        self.data_subscriber.set_shape(self.shape)
        self.data_publisher.set_shape(self.shape)

        self.poller.register(self.data_subscriber.socket, zmq.POLLIN)
        self.publish_status()

    def stop(self):
        """Stops the subscription to data port."""
        if self.tracking:
            self.tracking = 0
            self.command_publisher.send("zaber stop_xy")
            self.publish_status()

    def start(self):
        """Start subscribing to image data."""
        if not self.tracking:
            self.pid.Ix = 0
            self.pid.Iy = 0
            self.tracking = 1
            self.publish_status()

    def shutdown(self):
        """Shutdown the tracking device."""
        self.stop()
        self.running = 0
        self.publish_status()

    def update_status(self):
        """updates the status dictionary."""
        self.status["shape"] = self.shape
        self.status["tracking"] = self.tracking
        self.status["device"] = self.running


    def publish_status(self):
        """Publishes the status to the hub and logger."""
        self.update_status()
        self.command_publisher.send("hub " + json.dumps({self.name: self.status}, default=int))
        self.command_publisher.send("logger " + json.dumps({self.name: self.status}, default=int))

    def run(self):
        """This subscribes to images and adds time stamp
         and publish them with TimeStampedPublisher."""

        while self.running:

            sockets = dict(self.poller.poll())

            if self.command_subscriber.socket in sockets:
                self.command_subscriber.handle()

            elif self.data_subscriber.socket in sockets:
                self.process()

def main():
    """Create and start auto tracker device."""

    arguments = docopt(__doc__)
    device = TrackerDevice(
        commands_in=parse_host_and_port(arguments["--commands_in"]),
        data_in=parse_host_and_port(arguments["--data_in"]),
        commands_out=parse_host_and_port(arguments["--commands_out"]),
        data_out=parse_host_and_port(arguments["--data_out"]),
        fmt=arguments["--format"])

    device.run()

if __name__ == "__main__":
    main()
