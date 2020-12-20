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


## 1_python_script

We are going to adapt this excellent [blog post](https://www.pragmaticlinux.com/2020/12/monitor-cpu-and-ram-usage-in-python-with-psutil/) to create our system monitor script.

```
python3 -m venv venv
source venv/bin/activate
echo psutil==5.8.0 > requirements.txt
pip install -r requirements.txt
touch sysmon.py
```

1. Edit `sysmon.py` in your preferred text editor and add in the following functions from the blog post:
   - `get_cpu_usage_pct`
   - `get_cpu_frequency`
   - `get_cpu_temp`
   - `get_ram_usage`
   - `get_ram_total`
2. Next, create a `main` function that calls each of these functions and populates a dictionary: `payload` and prints it.
   1. We will also add a `timestamp` to the payload for use in visualisations later.
3. Add a `while(1)` that calls this `main` function every 10 seconds.
4. Add an argument parser so we can pass the `interval` and a `device_id` as command line arguments.
5. Run the script with `python sysmon.py 10 my_iot_device_1`

You should see output similar to:
![sysmon.py output](1_python_script.png)
## TODO
- [x] Add LICENSE
- [ ] Add screenshots
- [ ] Add motivation