#!/usr/bin/env python3

import os
import time
from datetime import datetime
import argparse
import sysmon
import aws_shadow_updater as aws_iot

def get_aws_iot_certs(device_id):
    certs_dir = os.getenv('CERTS_DIR')
    root_ca_cert = os.path.join(certs_dir, "AmazonRootCA1.pem") # Adjust per your Root CA settings
    device_cert = os.path.join(certs_dir, "{}-certificate.pem.crt".format(device_id))
    device_private_key = os.path.join(certs_dir, "{}-private.pem.key".format(device_id))
    assert os.path.exists(root_ca_cert), "Root CA Certificate not found"
    assert os.path.exists(device_cert), "Device Certificate not found"
    assert os.path.exists(device_private_key), "Device Private Key not found"
    return root_ca_cert, device_cert, device_private_key

def get_shadow_handler(device_id):
    """
    Given a device_id, creates a configuration for connecting to AWS IoT, creates and returns a device_shadow_handler.
    """
    # Get certificates for AWS IoT
    root_ca_cert, device_cert, device_private_key = get_aws_iot_certs(device_id)
    # Put the config together as a dictionary
    aws_iot_config = {
        "host": os.getenv("AWS_IOT_HOST"),
        "useWebsocket": False,
        "rootCAPath": root_ca_cert,
        "certificatePath": device_cert,
        "privateKeyPath": device_private_key,
        "thingName": device_id
    }
    return aws_iot.init_device_shadow_handler(aws_iot_config)

def get_metrics():
    """
    Groups the metrics together into an object that we can print to the terminal and/or 
    send to AWS IoT.
    """
    # Create dictionary with the metrics of interest
    metrics = {
        "cpu_usage": sysmon.get_cpu_usage_pct(),
        "cpu_freq": sysmon.get_cpu_frequency(),
        "cpu_temp": sysmon.get_cpu_temp(),
        "ram_usage": sysmon.get_ram_usage(),
        "ram_total": sysmon.get_ram_total(),
        "timestamp": int(datetime.now().timestamp()),
    }
    return metrics

def main(handler):
    """ Gets system metrics and updates the device shadow suing the aws_shadow_updater helper library.
    """
    payload = get_metrics()
    print("On device:", payload)
    aws_iot.update_device_shadow(handler, payload)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Continuously monitor and report system metrics.')
    parser.add_argument('interval', metavar='INTERVAL', type=int,
                        help='reporting interval in seconds')
    parser.add_argument('device_id', metavar='DEVICE_ID',
                        help='id of this device')
    args = parser.parse_args()
    device_shadow_handler = get_shadow_handler(args.device_id)
    while(1):
        main(device_shadow_handler)
        time.sleep(args.interval)