
import paho.mqtt.client as mqtt
import json
import numpy as np

# broker
IP = '130.192.92.239'
PORT = 1882

"""
examples of topic;
incitev/uc4/smartcharging/setpoint/ctrlEvcs0.Serverconnection

"""

def onMessage(client, userdata, message):
    global msg
    payLoad     = message.payload
    msg = json.loads(payLoad.decode('utf-8'))
    print(msg)
    try:
        id_cs = msg["id"]
        id_cs = id_cs.replace("/", "")
        id_cs = "cs1"
    except:
        pass

    id_evse = 1
    setpoints_message = {
      "id": id_cs,
      "csChargingProfiles": {
        "chargingProfileId": 158798,
        "chargingProfileKind": "Absolute",
        "chargingProfilePurpose": "TxProfile",
        "chargingSchedule": {
          "chargingRateUnit": "W",
          "chargingSchedulePeriod": [
            {
              "limit": 11000,
              "startPeriod": 0
            },
            {
              "limit": 9000,
              "startPeriod": 780
            },
            {
              "limit": 4500,
              "startPeriod": 1680
            }
          ],
          "duration": 1680
        },
        "stackLevel": 0,
        "transactionId": 339373,
        "validFrom": "2020–10–15T14:32:00+00:00",
        "validTo": "2020–10–16T14:15:00+00:00"
      }
    }

    topic_setpoint = 'incitev/uc4/smartcharging/setpoint/'+id_cs+"/"+str(id_evse)
    print(topic_setpoint)
    client.publish(topic_setpoint, json.dumps(setpoints_message))

def onConnect(mqttc, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    if rc!=0 :
        mqttc.reconnect()


client               = mqtt.Client()
client.on_message    = onMessage
client.on_connect    = onConnect
client.connect(IP, PORT)

TOPICS = [('incitev/uc4/smartcharging/status/cs',0)]
# TOPICS = [('/incitev/uc4/forecast_long_trigger',0)]

client.subscribe(TOPICS)

client.loop_forever()
