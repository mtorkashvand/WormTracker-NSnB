#! python
#
# Copyright 2021
# Author: Vivek Venkatachalam, Mahdi Torkashvand
#
# This is a convertor of messages from the PROCESSOR
# into stage commands for Zaber stages.
# Author: Vivek Venkatachalam, Mahdi Torkashvand

"""
This converts raw controller output to discrete events.

Usage:
    commands.py             [options]

Options:
    -h --help               Show this help.
    --inbound=HOST:PORT     Connection for inbound messages.
                                [default: L6001]
    --outbound=HOST:PORT    Connection for outbound messages.
                                [default: 6002]
    --console               Stream to stdout.
"""

import time
import signal
from typing import Tuple

from docopt import docopt

from wormtracker_scope.zmq.publisher import Publisher
from wormtracker_scope.zmq.subscriber import Subscriber
from wormtracker_scope.zmq.utils import parse_host_and_port

class XboxStageCommands():

    def __init__(self,
                 inbound: Tuple[str, int],
                 outbound: Tuple[str, int]):

        self.subscriber = Subscriber(inbound[1],
                                     inbound[0],
                                     inbound[2])

        self.publisher = Publisher(outbound[1],
                                   outbound[0],
                                   outbound[2])

        buttons = [
            b"X pressed", b"Y pressed", b"B pressed",
            b"A pressed",
            b"dpad_up pressed", b"dpad_up released",
            b"dpad_down pressed", b"dpad_down released",
            b"right_stick", b"left_stick",
            b"left_shoulder pressed", b"right_shoulder pressed"
            ]

        self.subscriber.remove_subscription("")
        for button in buttons:
            self.subscriber.add_subscription(button)

    def run(self):
        tracking_state = False
        recording_state = False
        led_state = False
        def _finish(*_):
            raise SystemExit

        signal.signal(signal.SIGINT, _finish)

        while True:
            message = self.subscriber.recv_last_string()

            if message is None:
                time.sleep(0.01)
                continue

            tokens = message.split(" ")
            if message == "B pressed":
                if recording_state:
                    self.publish("writer stop")
                    recording_state = False
                else:
                    self.publish("writer start")
                    recording_state = True
            
            elif message == "X pressed":
                if led_status:
                    self.publish("teensy_commands set_led 0")
                    led_status = False
                else:
                    self.publish("teensy_commands set_led 1")
                    led_status = True

            elif message == "A pressed":
                if tracking_state:
                    self.publish("tracker stop")
                    tracking_state = False
                else:
                    self.publish("tracker start")
                    tracking_state = True

            elif message == "Y pressed":
                self.publish("tracker stop")
                self.publish("writer stop")
                self.publish("teensy_commands movex 0")
                self.publish("teensy_commands movey 0")
                self.publish("teensy_commands movez 0")
                recording_state = False
                tracking_state = False

            elif message == "dpad_up pressed":
                self.publish("teensy_commands start_z_move 1")

            elif message == "dpad_up released":
                self.publish("teensy_commands movez 0")

            elif message == "dpad_down pressed":
                self.publish("teensy_commands start_z_move -1")

            elif message == "dpad_down released":
                self.publish("teensy_commands movez 0")

            elif message == "left_shoulder pressed":
                self.publish("teensy_commands change_vel_z -1")

            elif message == "right_shoulder pressed":
                self.publish("teensy_commands change_vel_z 1")

            elif tokens[0] == "left_stick":
                xspeed = int(tokens[1] // 5)
                yspeed = int(tokens[2] // 5)
                self.publish("teensy_commands movey {}".format(yspeed))
                self.publish("teensy_commands movex {}".format(xspeed))

            elif tokens[0] == "right_stick":
                xspeed = int(tokens[1])
                yspeed = int(tokens[2])
                self.publish("teensy_commands movey {}".format(yspeed))
                self.publish("teensy_commands movex {}".format(xspeed))

            else:
                print("Unexpected message received: ", message)

    def publish(self, verb, *args):
        command = verb
        for arg in args:
            command += " " + str(arg)
        self.publisher.send(command)

def main():
    """CLI entry point."""
    arguments = docopt(__doc__)

    inbound = parse_host_and_port(arguments["--inbound"])
    outbound = parse_host_and_port(arguments["--outbound"])

    processor = XboxStageCommands(inbound, outbound)

    processor.run()

if __name__ == "__main__":
    main()






