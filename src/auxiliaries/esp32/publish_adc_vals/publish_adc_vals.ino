/*
 * The current code does:
    *  connects to WIFI 
    *  Connects to a brocker (with no tls)
    *  published data on certain topic

TODO:
  - sampling from ADC
  - use differntial ADC mode

NOTE:
  - When connected to WiFi the ADC2 doesn't work:
  https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/peripherals/adc.html
  
 
*/

#include "WiFi.h" // ESP32 WiFi include
#include "include/WiFiConfig.h" // WiFi configuration.
#include "PubSubClient.h" // MQTT library

#include <time.h> 
#include <stdlib.h>

WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient); 
//char *mqttServer = "broker.hivemq.com";
//int mqttPort = 1883;
char *mqttServer = "mqtt.watt.linksfoundation.com";
int mqttPort = 1882;


const int Analog_channel_pin1= 32;
const int Analog_channel_pin2= 33;
int ADC_VALUE_1 = 0;
int ADC_VALUE_2 = 0;
int voltage_value = 0; 
int differntial_value = 0;

void setup() {
  Serial.begin(9600); 
  ConnectToWiFi();
  setupMQTT();
}

void loop() {
  delay(5000);

  // TODO I need to add some check every X seconds for WiFi connection
  // TODO I need to loop over possible networks always  
  if (!mqttClient.connected())
    reconnect();
  mqttClient.loop();

  ADC_VALUE_1 = analogRead(Analog_channel_pin1);
  ADC_VALUE_2 = analogRead(Analog_channel_pin2);
  Serial.print("ADC VALUE 1 = ");
  Serial.println(ADC_VALUE_1);
 Serial.print("ADC VALUE 2 = ");
  Serial.println(ADC_VALUE_2);
  delay(1000);
  differntial_value = ADC_VALUE_1 - ADC_VALUE_2;
//  voltage_value = (differntial_value * 3.3 ) / (4095);
//  Serial.print("Voltage = ");
//  Serial.print(voltage_value);
//  Serial.print(" volts");


  Serial.println("Differntial value is :");
  Serial.print(differntial_value);
  Serial.println("\n");


  /*srand(time(NULL)); 
  float val =  (float)rand()/(float)(RAND_MAX);
  */
  char buf[16];
  sprintf(buf, "%f", voltage_value);
  Serial.println(voltage_value);
  Serial.println(buf);
  mqttClient.publish("/incitev/uc4/forecast_long_trigger", buf);

}


void setupMQTT()
{
  mqttClient.setServer(mqttServer, mqttPort);
  //mqttClient.setCallback(callback);
}

void reconnect() {
  Serial.println("Connecting to MQTT Broker...");
  while (!mqttClient.connected()) {
      Serial.println("Reconnecting to MQTT Broker..");
      String clientId = "ESP32Client-";
      clientId += String(random(0xffff), HEX);
      
      if (mqttClient.connect(clientId.c_str())) {
        Serial.println("Connected.");
        // subscribe to topic
        mqttClient.subscribe("/swa/commands");
      }
  }
}



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
 
    if ((++i % 16) == 0)
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
