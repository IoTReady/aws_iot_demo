# AWS IoT Demo

## What are we going to build?

A metal-to-alerts example of how to build an IoT enabled monitoring solution using only AWS PaaS offerings. To achieve this, we will:

1. Write a Python script that monitors system metrics (CPU, Memory, Temperature, Fan)
   1. You could replace this with actual hardware, perhaps run this script on an Raspberry Pi or even send FreeRTOS metrics from ESP32 but we will save that for another day.
2. Create multiple `things` on AWS IoT Core using [Bulk Registration](https://docs.aws.amazon.com/iot/latest/developerguide/bulk-provisioning.html?icmpid=docs_iot_console) to speed things up.  
3. Send these metrics as shadow updates to AWS IoT every 10s (configurable)
4. Configure AWS IoT to route shadow updates to a database
5. Set up a visualisation tool and create dashboards using these updates 
6. Add a few simple alerts on our visualiation tool to send notifications if system metrics cross a threshold

### Approach #1

PyScript --> AWS_IoT --> AWS_Timestream --> Grafana

### Approach #2

PyScript --> AWS_IoT --> S3 --> QuickSight

### Approach #3

PyScript --> AWS_IoT --> S3 --> Athena --> Redash

## Git Repo Structure

- `master` = final code + AWS IoT configuration + Grafana dashboard JSON
- `1_python_script` = Python script without AWS IoT integration (print to console)
- `2_aws_iot` = Python script with AWS IoT integration (shadow updates)


## TODO
- [ ] Add LICENSE
- [ ] Add screenshots
- [ ] Add motivation