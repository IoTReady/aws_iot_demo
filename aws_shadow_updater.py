from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTShadowClient
import json

# Shadow JSON schema:
#
# Name: Bot
# {
#	"state": {
#		"desired":{
#			"property":<INT VALUE>
#		}
#	}
# }

# Custom Shadow callback
def shadow_update_callback(payload, responseStatus, token):
    if responseStatus == "timeout":
        print("Update request " + token + " time out!")
    if responseStatus == "accepted":
        payloadDict = json.loads(payload)
        print("On AWS IoT: ", payloadDict.get("state").get("reported"))
    if responseStatus == "rejected":
        print("Update request " + token + " rejected!")

def shadow_delete_callback(payload, responseStatus, token):
    if responseStatus == "timeout":
        print("Delete request " + token + " time out!")
    if responseStatus == "accepted":
        print("~~~~~~~~~~~~~~~~~~~~~~~")
        print("Delete request with token: " + token + " accepted!")
        print("~~~~~~~~~~~~~~~~~~~~~~~\n\n")
    if responseStatus == "rejected":
        print("Delete request " + token + " rejected!")

def init_device_shadow_handler(args):
    host = args.get("host")
    rootCAPath = args.get("rootCAPath")
    certificatePath = args.get("certificatePath")
    privateKeyPath = args.get("privateKeyPath")
    port = args.get("port")
    useWebsocket = args.get("useWebsocket")
    thingName = args.get("thingName")
    clientId = args.get("clientId")
    
    if not clientId: # Use thingName as clientId if not provided separately
        clientId = thingName

    if useWebsocket and certificatePath and privateKeyPath:
        print("X.509 cert authentication and WebSocket are mutual exclusive. Please pick one.")
        exit(2)

    if not useWebsocket and (not certificatePath or not privateKeyPath):
        print("Missing credentials for authentication.")
        exit(2)

    # Port defaults
    if useWebsocket and not port:  # When no port override for WebSocket, default to 443
        port = 443
    if not useWebsocket and not port:  # When no port override for non-WebSocket, default to 8883
        port = 8883

    # Init AWSIoTMQTTShadowClient
    myAWSIoTMQTTShadowClient = None
    if useWebsocket:
        myAWSIoTMQTTShadowClient = AWSIoTMQTTShadowClient(clientId, useWebsocket=True)
        myAWSIoTMQTTShadowClient.configureEndpoint(host, port)
        myAWSIoTMQTTShadowClient.configureCredentials(rootCAPath)
    else:
        myAWSIoTMQTTShadowClient = AWSIoTMQTTShadowClient(clientId)
        myAWSIoTMQTTShadowClient.configureEndpoint(host, port)
        myAWSIoTMQTTShadowClient.configureCredentials(rootCAPath, privateKeyPath, certificatePath)

    # AWSIoTMQTTShadowClient configuration
    myAWSIoTMQTTShadowClient.configureAutoReconnectBackoffTime(1, 32, 20)
    myAWSIoTMQTTShadowClient.configureConnectDisconnectTimeout(10)  # 10 sec
    myAWSIoTMQTTShadowClient.configureMQTTOperationTimeout(5)  # 5 sec

    # Connect to AWS IoT
    myAWSIoTMQTTShadowClient.connect()

    # Create a deviceShadow with persistent subscription
    deviceShadowHandler = myAWSIoTMQTTShadowClient.createShadowHandlerWithName(thingName, True)

    # Delete existing shadow JSON doc
    deviceShadowHandler.shadowDelete(shadow_delete_callback, 5)

    return deviceShadowHandler

def update_device_shadow(handler, payload):
    json_payload = json.dumps({
        "state": {
            "reported": payload
        }
    })
    handler.shadowUpdate(json_payload, shadow_update_callback, 5)
