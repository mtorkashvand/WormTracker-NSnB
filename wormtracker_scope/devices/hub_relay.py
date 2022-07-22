#! python
#
# Copyright 2022
# Author: Mahdi Torkashvand, Vivek Venkatachalam

"""
This handles commands involving multiple devices.

Usage:
    hub_relay.py                        [options]

Options:
    -h --help                           Show this help.
    --server=PORT                        Connection with the clinet.
                                            [default: 5002]
    --inbound=PORT                      Incoming from forwarder.
                                            [default: L5001]
    --outbound=PORT                     outgoing to forwarder.
                                            [default: L5000]
    --name=NAME                         device name.
                                            [default: hub]
    --framerate=NUMBER                  camera frame rate
                                            [default: 1]
    
"""

# import os
# import json
import time
# from typing import Tuple

from docopt import docopt

from wormtracker_scope.zmq.hub import Hub
from wormtracker_scope.zmq.utils import parse_host_and_port
# from wormtracker_scope.devices.utils import array_props_from_string

class WormTrackerHub(Hub):
    """This is a central hub that is responsible for subscribing and publishing
    messages to all components of Lambda. Clients controlling the microscope
    should communicate only with this."""
    def __init__(
            self,
            inbound,
            outbound,
            server,
            framerate,
            name="hub"):

        Hub.__init__(self, inbound, outbound, server, name)
        self.framerate=framerate

    def toggle_recording(self, state):
        if state in ["true", "True", "1", 1, True]:
            self._writer_start()
        else:
            self._writer_stop()

    def shutdown(self):
        self._displayer_shutdown()
        self._writer_shutdown()
        self._flir_camera_shutdown()
        self._data_hub_shutdown()
        self._tracker_shutdown()
        self._writer_shutdown()
        self._displayer_shutdown()
        self._teensy_commands_shutdown()
        time.sleep(0.5)
        self._logger_shutdown()
        self.running = False


    def _tracker_shutdown(self):
        self.send("tracker shutdown")

    def _logger_shutdown(self):
        self.send("logger shutdown")

    def _displayer_set_shape(self, y, x):
        self.send("displayer set_shape {} {}".format(y, x))

    def _displayer_shutdown(self):
        self.send("displayer shutdown")

    def _data_hub_set_shape(self, z, y, x):
        self.send("data_hub set_shape {} {}".format(y, x))

    def _data_hub_shutdown(self):
        self.send("data_hub shutdown")

    def _writer_set_saving_mode(self, saving_mode):
        self.send("writer set_saving_mode {}".format(saving_mode))

    def _writer_set_shape(self, y, x):
        self.send("writer set_shape {} {}".format(y, x))

    def _writer_start(self):
        self.send("writer start")

    def _writer_stop(self):
        self.send("writer stop")

    def _writer_shutdown(self):
        self.send("writer shutdown")

    def _flir_camera_start(self):
        self.send("FlirCamera start")

    def _flir_camera_stop(self):
        self.send("FlirCamera stop")

    def _flir_camera_shutdown(self):
        self.send("FlirCamera shutdown")

    def _flir_camera_set_exposure(self, exposure, rate):
        self.send("FlirCamera set_exposure {} {}".format(exposure, rate))
        time.sleep(1)
        self._flir_camera_start()

    def _flir_camera_set_height(self, height):
        self.send("FlirCamera set_height {}".format(height))

    def _flir_camera_set_width(self, width):
        self.send("FlirCamera set_width {}".format(width))

    def _teensy_commands_shutdown(self):
        self.send("teensy_commands shutdown")

    def _teensy_commands_set_led(self, led_status):
        self.send("teensy_commands set_led {}".format(led_status))

    def _teensy_commands_movex(self, xvel):
        self.send("teensy_commands movex {}".format(xvel))

    def _teensy_commands_movey(self, yvel):
        self.send("teensy_commands movey {}".format(yvel))

    def _teensy_commands_movez(self, zvel):
        self.send("teensy_commands movez {}".format(zvel))

    def _teensy_commands_disable(self):
        self.send("teensy_commands disable")
    
    def duration(self, sec):
        self.send("writer set_duration {}".format(sec*self.framerate))

def main():
    """This is the hub for lambda."""
    arguments = docopt(__doc__)

    scope = WormTrackerHub(
        inbound=parse_host_and_port(arguments["--inbound"]),
        outbound=parse_host_and_port(arguments["--outbound"]),
        server=int(arguments["--server"]),
        framerate=int(arguments["--framerate"]),
        name=arguments["--name"])

    scope.run()

if __name__ == "__main__":
    main()
