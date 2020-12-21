# AWS IoT Demo

## What are we going to build?

A metal-to-alerts example of how to build an IoT enabled monitoring solution using only AWS PaaS offerings. To achieve this, we will:

1. Write a Python script that monitors system metrics (CPU, Memory, Temperature, Fan)
   1. You could replace this with actual hardware, perhaps run this script on an Raspberry Pi or even send FreeRTOS metrics from ESP32 but we will save that for another day.
2. Create multiple `things` on AWS IoT Core.  
3. Send these metrics as shadow updates to AWS IoT every 10s (configurable)
4. Configure AWS IoT to route shadow updates to a database
5. Set up a visualisation tool and create dashboards using these updates 
6. Add a few simple alerts on our visualiation tool to send notifications if system metrics cross a threshold

## Git Repo Structure

- `master` = final code + AWS IoT configuration + Grafana dashboard JSON
- `1_python_script` = Python script without AWS IoT integration (print to console)
- `2_aws_iot` = Python script with AWS IoT integration (shadow updates)


## 1 - Python Script For System Metrics

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


## 2 - AWS IoT Integration

Now, we will add in the ability to send our metrics to AWS IoT. But first, we need to register our devices or `things` as AWS calls them.

### Registering the devices

We will register the devices individually via the AWS Console. However, if you have a large number of devices to register, you may want to script it or use [Bulk Registration](https://docs.aws.amazon.com/iot/latest/developerguide/provision-template.html) via `aws-cli` or the AWS IoT Core Console. 

> We are using `us-east-1` aka N. Virginia for integration later with Amazon Timestream which is not yet available in all regions.

1. Click on `Create a single thing`
   1. Give your thing a name, e.g. `my_iot_device_1`
   2. You can skip `Thing Type` and `Group` for this demo.
   3. Create the thing
2. Use the `One-click certificate creation (recommended)` option to generate the certificates.
   1. Download the generated certificates and the root CA certificate.
   2. Activate the certificates.
3. Attach a policy and register the `Thing`. 
   1. Because we are cavalier and this is a demo, we are using the following `PubSubToAny` policy. 
   2. **DO NOT** use this in production!

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "iot:*",
      "Resource": "*"
    }
  ]
}
```

Now repeat this a couple more times so we have a few things. I am setting up 3 devices with the imaginative names: `my_iot_device_1`, `my_iot_device_2`, `my_iot_device_3`.

Finally, we will rename our certificates to match our thing names so that it's easier to script together. For instance, I am using the rename utility to bulk rename my certificates:

![Bulk renaming certs](rename_certs.png)

### Adding the AWS IoT SDK

Because AWS IoT supports MQTT, we could use any MQTT client that supports X.509 certificates. However, to keep things simple, we will use the [official Python SDK](https://github.com/aws/aws-iot-device-sdk-python) from AWS IoT. Specifically, we will adapt the [`basicShadowUpdater.py` sample](https://github.com/aws/aws-iot-device-sdk-python/blob/master/samples/basicShadow/basicShadowUpdater.py).

- Please inspect `aws_shadow_upater.py` for the changes we are making. Primarily, we are wrapping the functionality into 2 functions:
  - `init_device_shadow_handler` that takes AWS IoT specific config parameters and returns a `deviceShadowHandler` specific to our configuration and thing.
  - `update_device_shadow` that takes our system metrics payload and wraps it into a `json` structure that AWS IoT expects for `device shadows`. 
- We will also take this opportunity to modularise our code a bit by moving the `main` function from `sysmon.py` into its own separate file.
- Within `main.py` we are reading our AWS configuration from a combination of environment variables and the local certificates.
  - We only need the following: `export AWS_IOT_HOST=YOUR_AWS_IOT_ENDPOINT.amazonaws.com` and `export CERTS_DIR=certs` assuming you are keeping your certificates in `certs/`. 
  - You will probably want to create a script or `.env` file to set these environment variables
  - For good measure, we are also verifying that the certificates actually exist.
- With this done, we stitch our two modules `sysmon.py` and `aws_shadow_updater.py` together and start publishing updates. If all goes well, you should see the following in your terminal and your AWS Console (go to Thing -> Shadows -> Classic Shadow)

![Terminal Output](2_aws_iot_terminal.png)

![AWS Console](2_aws_iot_console.png)

## 3 - Simulating Multiple Devices

> We are done with almost all of the coding needed to get this working. 

This is an easy one, open up multiple terminals/tabs and start a separate process for updating the shadow for each `device`. Something like this:

![Multiple Devices](3_multiple_shadow_updates.png)

## 4 - Persisting Shadow Updates

In order to visualise, and perhaps analyse, these metrics, we need to persist them in some form of database. Thankfully, AWS IoT has a [Rules Engine](https://docs.aws.amazon.com/iot/latest/developerguide/iot-rules.html) designed for just this purpose. The Rules Engine is essentially a message router with the ability to filter messages using an SQL syntax and send them to various destiations.

Go to `AWS IoT Core -> Act -> Rules` to get started. 

There are 2 steps to enabling rules:
1. Filter: Select the messages we want to act on.
2. Act: Select the action(s) we want to run for each filtered message.

### Filter

AWS IoT uses a reduced [SQL syntax](https://docs.aws.amazon.com/iot/latest/developerguide/iot-sql-reference.html) for filtering messages. Points to note:

- The [shadow topic](https://docs.aws.amazon.com/iot/latest/developerguide/device-shadow-mqtt.html#update-pub-sub-topic) we are interested in is `$aws/things/thingName/shadow/update` where we need to replace `thingName` with the wildcard `+`. Follow [this reference](https://docs.aws.amazon.com/iot/latest/developerguide/topics.html) on topics and wildcards.
- The content of each message contains the entire `state` with `desired` and `reported` properties as well as other metadata. We will need to unpack the `reported` property to get the data we need. Follow [this reference](https://docs.aws.amazon.com/iot/latest/developerguide/iot-sql-select.html) for more details.

Our SQL filter will look essentially like this:

```sql
SELECT 
  state.reported.cpu_usage as cpu_usage,
  state.reported.cpu_freq as cpu_freq,
  state.reported.cpu_temp as cpu_temp,
  state.reported.ram_usage as ram_usage,
  state.reported.ram_total as ram_total,
  state.reported.timestamp as timestamp,
  clientid() as device_id,
  newuuid() as id
FROM '$aws/things/+/shadow/update'
```

**Notes**

- We are inserting the device_id using a [built-in SQL function](https://docs.aws.amazon.com/iot/latest/developerguide/iot-sql-functions.html) `clientid()`. We will need this for some of our Actions.
- We are inserting a new field called id into our dataset for use with some specific data persistence options. We will discuss these later. For now, feel free to skip it.

Before we can save this rule, we will also need to add an `action`. Actions define what to do with the filtered messages. This depends on our choice of database. 

### Act

AWS IoT supports a large range of actions out of the box including CloudWatch, DynamoDB, ElasticSearch, Timestream DB and custom HTTP endpoints. See the [full list here](https://docs.aws.amazon.com/iot/latest/developerguide/iot-rule-actions.html).

To confirm that our messages are coming through and we will be able to store them, we will use the `DynamoDBv2` action. We will also enable the `CloudWatch` action in case of errors.

#### DynamoDBv2

This action stores the metrics (`cpu_usage`, `cpu_freq` etc) in separate columns in the table. Use the guided flow to create the `aws_iot_demo` table and assign permissions. Use `id` as the `primaryKey` and skip the `sortKey`.

#### CloudWatch
This action is triggered if/when there is an error while processing our rule. Again, follow the guided wizard to create a new `Log Group` and assign permissions.

At the end, your rule should look something like this:

![AWS IoT Rule Summary](4_aws_iot_action_summary.png)


## 5 - Verification

Now, if you start the simulators again, you will see your DynamoDB table start to fill up. Here's what it should look like:

![DynamoDB Table With IoT Data](5_aws_dynamodb.png)


## Pause For Breath

We have covered a lot of ground. So, let's pause and reflect. Here's what we have done so far:

1. Created a Python script to monitor common system metrics.
2. Hooked up this script to AWS IoT using the SDK and `Thing` certificates.
3. Simulated running multiples of these devices with sending a `Shadow` update.
4. Created a rule to persist these device shadows to `DynamoDB` and errors to `CloudWatch`.
5. Verified that we are actually getting our data.


Here's the kicker, though. DynamoDB is *not* a great service to use for storing time series data. Querying can be quite slow and rich queries are **very** inconvenient despite the presence of third party efforts like [DQL](https://dql.readthedocs.io/en/latest/). So, in the next couple of sections we will evaluate our options for *actually using* the data our devices are generating. 

With a fresh cup of coffee, onwards...

## 6 - Storage and Visualisation

Storage and visualisation are, in fact, two separate operations that need two different software tools. However, these are often so tightly coupled that choice of one often dictates choice of the other. Here's a handy table that illustrates this with comments.

| Storage | Visualisation | Comments  |
| ---     | ---                   | ---       |
| DynamoDB | AWS QuickSight | Needs CSV export to S3 first |
| DynamoDB | Redash | Works via DQL, see demo below |
| Timestream | AWS QuickSight | Fidgety, see demo below |
| Timestream | Grafana | Buggy?, see demo below |
| ElasticSearch | Kibana | Works well, see demo below |
| ElasticSearch | Grafana | Simpler to just use Kibana |
| InfluxDB | InfluxDB UI | WIP |
| InfluxDB | Grafana | Simpler to just use the built-in UI |

There are, of course, numerous other ways to do this. Our goal is to compare some of the more obvious options and, perhaps, pick one that works well.

### DyanamoDB + ReDash

Since we already have data in DynamoDB, let's try and use it for querying and visualisations. We will use [Redash](https://redash.io/), an open source Python based BI tool. There's a cloud hosted version but I already have it running locally via Docker so I am going to use that instead. I won't cover setting up Redash locally, you can follow their [installation instructions](https://redash.io/help/open-source/setup#docker) and or just sign up for a cloud trial. FWIW, I am on version `8.0.0+b32245`.

Connecting to DynamoDB is pretty straightforward:

1. Add a `New Data Source` and search for `DynamoDB (with DQL)`
2. Enter a `Name`, `Access Key`, `Region` and `Secret Key`.
3. Save and click on `Test Connection` to ensure you are connected.

![Redash DynamoDB Data Source](6_redash_dynamodb.png)

Next, create a `New Query`. The simplest query to try out is `SCAN * FROM aws_iot_demo;`. In case you are wondering the `SCAN` keyword, check out the [DQL documentation](https://dql.readthedocs.io/en/latest/topics/queries/scan.html). 

> Despite creating indices on the DynamoDB table and following the DQL documentation, I could not get `SELECT` working.

This query will return ALL the data from our table. Careful when running on large tables! There *may* be some row limits imposed by either DQL or the AWS API. However, `SCAN` operations are quite slow as you can see from the screenshot below.

![Redash DynamoDB Query](6_redash_dynamodb_query.png)

Nonetheless, we have our data and we can quickly visualise it:

1. Click on `New Visualisation`. 
2. Select `Line` for `Chart Type`
3. Select `timestamp` for `X Column` and also, on the `X Axis` tab, change the `Scale` to `Datetime` from the default `Auto Detect`.
4. Select `cpu_usage` for `Y Columns` and `device_id` for `Group By`. Ensure `Show Legend` is checked.
5. Play around with the other settings and see what you like. 

Once you are done, you will see something that looks like this - 

![Redash Chart](6_redash_chart.png)

Uh, oh. Redash thinks our `timestamp` belongs to January, 1970. This is because Redash is expecting `milliseconds` and we are sending `seconds`. We could change our script and send milliseconds instead or even modify the timestamp within our AWS IoT Rule SQL query. However, I am trying to configure this within Redash. If/once I am able to figure this out, I will update this section.

You can create charts for the other metrics too and add them all to a Dashboard:

![Redash Dashboard](6_redash_dashboard.png)

Nice! Our first IoT dashboard that can refresh in realtime :-). If you use the cloud version of Redash and don't mind the slow query speeds with DynamoDB, you have a highly scalable end-to-end solution! However, this setup will get slower with time and very expensive unless you archive old data within DynamoDB.

### Timestream DB + QuickSight / Grafana

As of this writing Timestream is only available in 4 regions. 

![Timestream Regions](aws_timestream_regions.png)

It's **essential** to create the DB in the same region as your AWS IoT endpoint as the Rules Engine does not, yet, support multiple regions for the built-in actions. _You could use a Lambda function to do this for you but that's more management and cost.

We will create a `Standard` (empty) DB with the name `aws_iot_demo`: 

![Create Timestream DB](6_create_timestream_db.png)

We will also need a `table` to store our data, so let's do that too:

![Create Timestream Table](6_create_timestream_table.png)

Once this is done, we can return to the rule we set up earlier and add a new Action.

Notes: 
- The AWS IoT Rule Action for Timestream needs at least one [`dimension`](https://docs.aws.amazon.com/iot/latest/developerguide/timestream-rule-action.html) to be specified. Dimensions can be used for grouping and filtering incoming data. 
- I used the following `key`:`value` pair using a substitution template - `device_id`: `${clientId()}` 
  - This conflicts with the `device_id` we are adding in the SQL query. So, either remove that or use a different key name here. 
- We are sending the device timestamp as part of the shadow update. I couldn't figure out how to use this as the timestamp in Timestream so I used `${timestamp()}` within the Rule Action. This generates a server timestamp.
- You will also need to create or select an appropriate IAM role that lets AWS IoT to write to Timestream.
- Timestream (like InfluxDB) creates separate rows for each metric so each shadow update creates 7 rows. 

#### Query Timestream

Assuming we have started our simulators again, we should start to see data being stored in Timestream. Go over to AWS Console -> Timestream -> Tables ->  `aws_iot_demo` -> Query Table. Type in the following query:

```sql
-- Get the 20 most recently added data points in the past 15 minutes. You can change the time period if you're not continuously ingesting data
SELECT * FROM "aws_iot_demo"."aws_iot_demo" WHERE time between ago(15m) and now() ORDER BY time DESC LIMIT 20
```

You should see output similar to the one below:

![Timestream Query Output](6_timestream_query_output.png)

If you do, you are in business and we can continue to visualisation. If you don't,

- Check the Cloudwatch Logs for errors
- Verify that your SQL syntax is correct - especially the topic
- Ensure your Rule action has the right table and an appropriate IAM Role
- Verify that your Device Shadow is getting updated by going over to AWS IoT -> Things -> my_iot_device_1 -> Shadow
- Looking for errors if any on the terminal where you are running the script.

#### Dashboards Using AWS Quicksight

Quicksight is a managed BI tool from AWS. The [official documentation](https://docs.aws.amazon.com/timestream/latest/developerguide/Quicksight.html) to integrate Timestream with Quicksight is a little dense. However, it's pretty straightforward if you are using `us-east-1` as your region. 

1. Within Quicksight, click on the user icon at the top right and then on `Manage Quicksight`.
2. Here, go to `Security & Permissions` -> `Quicksight access to AWS services` and enable `Timestream` (see image below).
3. Next, within Quicksight, click on `New Dataset` and select `Timestream`. Click on `Validate Connection` to ensure you have given the permissions and confirm.
4. Upon confirmation, select `aws_iot_demo` from the discovered databases and select `aws_iot_demo` from the tables.

So far so good. This is where it gets quite complex. This is what my dashboard looks like after about 5-10 minutes of fiddling:

![QuickSight Timestream Dashboard](6_timestream_quicksight_dashboard.png)

Simple bar charts are easy to. However, I believe, to get time series charts working we will need to use a custom query instead of the `aws_iot_demo` table in `Step 4` above. The [documentation and examples](https://docs.aws.amazon.com/timestream/latest/developerguide/sample-queries.iot-scenarios.html#sample-queries.iot-scenarios.example-queries) for complex Timeseries queries are a little involved, so I might return to this later.


#### Dashboards & Alerts Using Grafana

AWS has an upcoming managed [Grafana service](https://aws.amazon.com/grafana/). Until then, we will use the managed service from [Grafana.com](https://grafana.com). You could also spin up Grafana locally or on a VM somewhere with the [docker image](https://grafana.com/docs/grafana/latest/installation/docker/).

Assuming you have either signed up for Grafana Cloud or installed it locally, you should now:

- Install the [Amazon Timestream plugin](https://grafana.com/grafana/plugins/grafana-timestream-datasource/installation)
- Back in Grafana, add a new `Data Source` and search for `Timestream`. 
- For authentication, we will use Access Key and Secret for a new IAM User.
  - Back in AWS, create a new user with the ~`AmazonTimestreamReadOnlyAccess` policy attached~ `admin` rights. For some reason, Grafana would not connect to Timestream even with the `AmazonTimestreamFullAccess` policy attached.  
- Once the keys are in place, click on `Save & Test`
- Select `aws_iot_demo` in the `$_database` field to set up the default DB. Try as I might, I could not get the dropdown for `$_table` to populate.

![Grafana Timestream Settings](6_grafana_timestream_settings.png)

Now, click on `+ -> Dashboard` and `+ Add new panel` to get started.


## TODO
- [x] Add LICENSE
- [x] Add screenshots
- [ ] Add motivation