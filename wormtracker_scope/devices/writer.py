#! python
#
# Copyright 2021
# Author: Mahdi Torkashvand, Vivek Venkatachalam

"""
Subscribes to a binary stream over TCP and saves the messages to a file.

Usage:
    writer.py                           [options]

Options:
    -h --help                           Show this help.
    --data_in=HOST:PORT                 Connection for inbound array data.
                                            [default: localhost:5004]
    --commands_in=HOST:PORT             Connection for commands.
                                            [default: localhost:5001]
    --status_out=HOST:PORT              Socket Address to publish status.
                                            [default: localhost:5000]
    --directory=PATH                    Directory to write data to.
                                            [default: ]
    --format=FORMAT                     Size and type of image being sent.
                                            [default: UINT8_YX_512_512]
    --video_name=NAME                   Directory to write data to.
                                            [default: data]
    --name=NAME                         Device name.
                                            [default: writer]
"""

from typing import Tuple
import multiprocessing
import json
import time

import zmq
from docopt import docopt

from wormtracker_scope.writers.array_writer import TimestampedArrayWriter
from wormtracker_scope.zmq.array import TimestampedSubscriber
from wormtracker_scope.zmq.subscriber import ObjectSubscriber
from wormtracker_scope.zmq.publisher import Publisher
from wormtracker_scope.devices.utils import make_timestamped_filename
from wormtracker_scope.zmq.utils import parse_host_and_port
from wormtracker_scope.devices.utils import array_props_from_string

class  WriteSession(multiprocessing.Process):
    """This is hdf_writer class"""

    def __init__(
            self,
            data_in: Tuple[str, int],
            commands_in: Tuple[str, int],
            status_out: Tuple[str, int],
            fmt: str,
            directory: str,
            name="writer",
            video_name="data"):

        multiprocessing.Process.__init__(self)

        self.status = {}
        self.device_status = 1
        self.subscription_status = 0
        self.counter = 0
        self.max_frame_no = 200


        self.name = name
        self.video_name = video_name

        (self.dtype, _, self.shape) = array_props_from_string(fmt)
        self.file_name = "TBS"
        self.data_in = data_in
        self.directory = directory
        self.poller = zmq.Poller()

        self.status_publisher = Publisher(
            host=status_out[0],
            port=status_out[1],
            bound=status_out[2])

        self.command_subscriber = ObjectSubscriber(
            obj=self,
            name=name,
            host=commands_in[0],
            port=commands_in[1],
            bound=commands_in[2])

        self.data_subscriber = TimestampedSubscriber(
            host=self.data_in[0],
            port=self.data_in[1],
            shape=self.shape,
            datatype=self.dtype,
            bound=self.data_in[2])

        self.poller.register(self.command_subscriber.socket, zmq.POLLIN)
        self.poller.register(self.data_subscriber.socket, zmq.POLLIN)

    def set_shape(self, y, x):
        """Updates the shape, closes the data subscriber, creates a new data subscriber"""
        self.shape = (y, x)
        self.poller.unregister(self.data_subscriber.socket)
        self.data_subscriber.set_shape(self.shape)
        self.poller.register(self.data_subscriber.socket, zmq.POLLIN)

    def start(self):
        if not self.subscription_status:
            self.filename = make_timestamped_filename(self.directory,
                                                      self.video_name, "h5")

            self.writer = TimestampedArrayWriter.from_source(self.data_subscriber,
                                                             self.filename)
            self.subscription_status = 1
            print("Recording Started.")

    def stop(self):
        """Closes the hdf file, updates the status. """
        if self.subscription_status:
            self.subscription_status = 0
            self.counter =0
            self.writer.close()
            print("Recording Ended.")

    def shutdown(self):
        """Close the hdf file and end while true loop of the poller"""
        self.stop()
        self.device_status = 0

    def run(self):
        """Start a while true loop with a poller that has command_subscriber already registered."""

        while self.device_status:

            sockets = dict(self.poller.poll())

            if self.command_subscriber.socket in sockets:
                _ = self.data_subscriber.get_last()
                self.command_subscriber.handle()


            elif self.subscription_status : 
                if self.counter < self.max_frame_no :

                    if self.data_subscriber.socket in sockets:
                        self.writer.save_frame()
                        self.counter +=1
                else:
                    self.stop()

    def toggle(self) :
        if self.subscription_status :
            self.stop()

        else :
            self.start()

    def set_duration(self, duration):
        self.max_frame_no = duration
        print("the number of frames are set to: {}, and of course hello world!!".format(duration))

def main():
    """CLI entry point."""

    args = docopt(__doc__)

    writer = WriteSession(
        data_in=parse_host_and_port(args["--data_in"]),
        commands_in=parse_host_and_port(args["--commands_in"]),
        status_out=parse_host_and_port(args["--status_out"]),
        fmt=args["--format"],
        directory=args["--directory"],
        name=args["--name"],
        video_name=args["--video_name"])

    writer.run()

if __name__ == "__main__":
    main()
