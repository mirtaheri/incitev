import time

import paho.mqtt.client as mqtt
import json
import numpy as np

message = {
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

# broker
IP = '130.192.92.239'
PORT = 1882


def onConnect(mqttc, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    if rc!=0 :
        mqttc.reconnect()


client               = mqtt.Client()
client.on_connect    = onConnect
client.connect(IP, PORT)


topic = 'incitev/uc4/smartcharging/setpoint/cs1'
while 1:
    client.publish(topic, json.dumps(message))
    time.sleep(5)
