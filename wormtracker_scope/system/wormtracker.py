#! python
#
# This runs wormtracker.
#
# Copyright 2022
# Author: Mahdi Torkashvand

"""
Run all wormtracker components.

Usage:
    wormtracker.py                      [options]

Options:
    -h --help                           Show this help.
    --format=FORMAT_STR                 Image format.
                                            [default: UINT8_YX_1536_1536]
    --camera_serial_number=SN           Camera Serial Number.
                                            [default: 21181595]
    --binsize=NUMBER                    Specify camera bin size.
                                            [default: 1]
    --exposure=VALUE                    Exposure time of flircamera in us.
                                            [default: 1000]
"""

import time
import os
import signal
from subprocess import Popen

from docopt import docopt

from wormtracker_scope.devices.utils import array_props_from_string

def execute(job, fmt: str, camera_serial_number: str, binsize: str, exposure: str):
    """This runs all devices."""

    forwarder_in = str(5000)
    forwarder_out = str(5001)
    server_client = str(5002)
    XInputToZMQPub_out = str(6000)
    processor_out = str(6001)
    data_camera_out = str(5003)
    data_stamped = str(5004)
    tracker_out = str(5005)

    (_, _, shape) = array_props_from_string(fmt)
    teensy_usb_port = "COM4"
    flir_exposure = exposure
    framerate = str(10)
    binsize = str(binsize)

    data_directory = "C:\workspace\wormtracker\data\hdf_writer"
    logger_directory = "C:\workspace\wormtracker\data\logs"
    if not os.path.exists(data_directory):
        os.makedirs(data_directory)
    if not os.path.exists(logger_directory):
        os.makedirs(logger_directory)

    job.append(Popen(["wormtracker_client",
                      "--port=" + server_client]))

    job.append(Popen(["XInputToZMQPub",
                      "--outbound=*:" + XInputToZMQPub_out]))

    job.append(Popen(["wormtracker_processor",
                      "--inbound=L" + XInputToZMQPub_out,
                      "--outbound=" + processor_out,
                      "--deadzone=5000",
                      "--threshold=50"]))

    job.append(Popen(["wormtracker_commands",
                      "--inbound=L" + processor_out,
                      "--outbound=L" + forwarder_in]))


    job.append(Popen(["wormtracker_hub",
                       "--server=" + server_client,
                       "--inbound=L" + forwarder_out,
                       "--outbound=L" + forwarder_in,
                       "--name=hub",
                       "--framerate="+ framerate]))

    job.append(Popen(["wormtracker_forwarder",
                      "--inbound=" + forwarder_in,
                      "--outbound=" + forwarder_out]))

    job.append(Popen(["FlirCamera",
                    "--serial_number=" + camera_serial_number,
                    "--commands=localhost:" + forwarder_out,
                    "--name=FlirCamera",
                    "--status=localhost:" + forwarder_in,
                    "--data=*:" + data_camera_out,
                    "--width=" + str(shape[1]),
                    "--height=" + str(shape[0]),
                    "--exposure_time=" + flir_exposure,
                    "--framerate=" + framerate,
                    "--binsize=" + binsize]))

    job.append(Popen(["wormtracker_data_hub",
                        "--data_in=L" + data_camera_out,
                        "--commands_in=L" + forwarder_out,
                        "--status_out=L" + forwarder_in,
                        "--data_out=" + data_stamped,
                        "--format=" + fmt,
                        "--name=data_hub"]))

    job.append(Popen(["wormtracker_writer",
                        "--data_in=L" + data_stamped,
                        "--commands_in=L" + forwarder_out,
                        "--status_out=L" + forwarder_in,
                        "--format=" + fmt,
                        "--directory="+ data_directory,
                        "--video_name=flircamera",
                        "--name=writer"]))

    job.append(Popen(["wormtracker_displayer",
                          "--inbound=L" + tracker_out,
                          "--format=" + fmt,
                          "--commands=L" + forwarder_out,
                          "--name=displayer"]))

    job.append(Popen(["wormtracker_logger",
                      "--inbound=" + forwarder_out,
                      "--directory=" + logger_directory]))

    job.append(Popen(["wormtracker_tracker",
                      "--commands_in=L" + forwarder_out,
                      "--commands_out=L" + forwarder_in,
                      "--data_in=L" + data_stamped,
                      "--data_out=" + tracker_out,
                      "--format=" + fmt]))

    job.append(Popen(["wormtracker_teensy_commands",
                      "--inbound=L" + forwarder_out,
                      "--outbound=L" + forwarder_in,
                      "--port=" + teensy_usb_port]))





def run(fmt: str, camera_serial_number: str, binsize: str, exposure: str):
    """Run all system devices."""

    jobs = []

    def finish(*_):
        for job in jobs:
            try:
                job.kill()
            except PermissionError as _e:
                print("Received error closing process: ", _e)

        raise SystemExit

    signal.signal(signal.SIGINT, finish)

    execute(jobs, fmt, camera_serial_number, binsize, exposure)

    while True:
        time.sleep(1)


def main():
    """CLI entry point."""
    args = docopt(__doc__)

    run(
        fmt=args["--format"],
        camera_serial_number=args["--camera_serial_number"],
        binsize=args["--binsize"],
        exposure=args["--exposure"]
    )

if __name__ == "__main__":
    main()
