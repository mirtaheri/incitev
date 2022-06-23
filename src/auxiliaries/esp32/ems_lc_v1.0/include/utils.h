
#include <math.h>
#include "./WiFiConfig.h" // WiFi configuration.
#include "./servers.h" // servers configuration.
#include "WiFi.h" // ESP32 WiFi include
#include "PubSubClient.h" // MQTT library

WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient); 


void control(void) {
	int a;
}

/*

void setupMQTT()
{
  mqttClient.setServer(mqttServer, mqttPort);
  //mqttClient.setCallback(callback);
}

void reconnect() {
  Serial.println("Connecting to MQTT Broker...");
  while (!mqttClient.connected()) {
    if (WiFi.status() != WL_CONNECTED)
    { // in a rare case if in this loop connection is droped this statement helps.
      ConnectToWiFi();
    }
    
    String clientId = "ESP32Client-";
    clientId += String(random(0xffff), HEX);
    Serial.print("Connecting to MQTT Broker by ID: ");
    Serial.println(clientId);

      if (mqttClient.connect(clientId.c_str())) {
        Serial.println("Connected.");
        // subscribe to topic
        mqttClient.subscribe("/swa/commands");
      }
      delay(500);
  }
}
*/

void ConnectToWiFi()
{
  WiFi.mode(WIFI_STA);
  WiFi.begin(SSID, WiFiPassword);
  Serial.print("Connecting to "); 
 
  uint8_t i = 0;
  uint8_t attempt_counter = 0;
  while (WiFi.status() != WL_CONNECTED)
  {
    Serial.print('.');
    delay(5000);
 
    if ((++i % 4) == 0)
    {
      Serial.println(F(" still trying to connect"));
      attempt_counter = attempt_counter + 1;
    }
    
    if (attempt_counter > 2)
    {
      Serial.println(F("****    Restarting microcontroller    ****"));
      ESP.restart();
      attempt_counter = 0;
    }
  }
 
  Serial.print(F("Connected. My IP address is: "));
  Serial.println(WiFi.localIP());
}

void setupMQTT()
{
  mqttClient.setServer(mqttServer, mqttPort);
  //mqttClient.setCallback(callback);
}


void reconnect() {
  Serial.println("Connecting to MQTT Broker...");
  while (!mqttClient.connected()) {
    if (WiFi.status() != WL_CONNECTED)
    { // in a rare case if in this loop connection is droped this statement helps.
      ConnectToWiFi();
    }
    
    String clientId = "ESP32Client-";
    clientId += String(random(0xffff), HEX);
    Serial.print("Connecting to MQTT Broker by ID: ");
    Serial.println(clientId);

      if (mqttClient.connect(clientId.c_str())) {
        Serial.println("Connected.");
        // subscribe to topic
        mqttClient.subscribe("/swa/commands");
      }
      delay(500);
  }
  mqttClient.loop();
}
