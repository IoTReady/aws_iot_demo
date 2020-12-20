#!/usr/bin/env python3

import os
import psutil
import time
from datetime import datetime
import argparse

def get_cpu_usage_pct():
    """
    Obtains the system's average CPU load as measured over a period of 500 milliseconds.
    :returns: System CPU load as a percentage.
    :rtype: float
    """
    return psutil.cpu_percent(interval=0.5)

def get_cpu_frequency():
    """
    Obtains the real-time value of the current CPU frequency.
    :returns: Current CPU frequency in MHz.
    :rtype: int
    """
    return int(psutil.cpu_freq().current)

def get_cpu_temp():
    """
    Obtains the current value of the CPU temperature.
    :returns: Current value of the CPU temperature if successful, zero value otherwise.
    :rtype: float
    """
    # Initialize the result.
    result = 0.0
    # The first line in this file holds the CPU temperature as an integer times 1000.
    # Read the first line and remove the newline character at the end of the string.
    if os.path.isfile('/sys/class/thermal/thermal_zone0/temp'):
        with open('/sys/class/thermal/thermal_zone0/temp') as f:
            line = f.readline().strip()
        # Test if the string is an integer as expected.
        if line.isdigit():
            # Convert the string with the CPU temperature to a float in degrees Celsius.
            result = float(line) / 1000
    # Give the result back to the caller.
    return result

def get_ram_usage():
    """
    Obtains the absolute number of RAM bytes currently in use by the system.
    :returns: System RAM usage in bytes.
    :rtype: int
    """
    return int(psutil.virtual_memory().total - psutil.virtual_memory().available)

def get_ram_total():
    """
    Obtains the total amount of RAM in bytes available to the system.
    :returns: Total system RAM in bytes.
    :rtype: int
    """
    return int(psutil.virtual_memory().total)

def main(device_id):
    """
    Groups the metrics together into an object that we can print to the terminal and/or 
    send to AWS IoT.
    """
    # Create dictionary with the metrics of interest
    payload = {
        "cpu_usage": get_cpu_usage_pct(),
        "cpu_freq": get_cpu_frequency(),
        "cpu_temp": get_cpu_temp(),
        "ram_usage": get_ram_usage(),
        "ram_total": get_ram_total(),
        "timestamp": int(datetime.now().timestamp())
    }
    # print metrics to stdout
    # later, we will replace this line and send the metrics to AWS IoT instead.
    print("Metrics for {}".format(device_id))
    print(payload)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Continuously monitor and report system metrics.')
    parser.add_argument('interval', metavar='INTERVAL', type=int,
                        help='reporting interval in seconds')
    parser.add_argument('device_id', metavar='DEVICE_ID',
                        help='id of this device')
    args = parser.parse_args()
    while(1):
        main(args.device_id)
        time.sleep(args.interval)