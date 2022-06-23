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


#include "./include/constants.h" // constants to be used.
#include "./include/struct_data_type.h" // constants to be used.
#include "./include/utils.h" // constants to be used.
#include "./include/control.h" // constants to be used.
#include <time.h> 
#include <stdlib.h>


int *dvdt;
Meter DYN_V;

void setup() {
  Serial.begin(9600);
  ConnectToWiFi();
  setupMQTT();
}

void loop() {
  delay(5000);
  // TODO I need to add some check every X seconds for WiFi connection --> done
  // TODO I need to loop over possible networks always  

  if (WiFi.status() != WL_CONNECTED)
  {
    Serial.println("Connection to WiFi is lost");
    Serial.println(WiFi.status());
    ConnectToWiFi();
  }
  
  if (!mqttClient.connected())
    reconnect();
  // TODO: I have to handle all the measurements reading from function for both voltage and current
   
  
  ADC_VALUE_1 = analogRead(Analog_channel_pin1);
  
  /*ADC_VALUE_2 = analogRead(Analog_channel_pin2);
  ADC_VALUE_3 = analogRead(Analog_channel_pin3);
  ADC_VALUE_4 = analogRead(Analog_channel_pin4);
  
  Serial.print("ADC VALUE 1 = ");
  Serial.println(ADC_VALUE_1);
  Serial.print("ADC VALUE 2 = ");
  Serial.println(ADC_VALUE_2);
  Serial.print("ADC VALUE 3 = ");
  Serial.println(ADC_VALUE_3);
  Serial.print("ADC VALUE 4 = ");
  Serial.println(ADC_VALUE_4);*/
  delay(DELAY);
  //differntial_value = ADC_VALUE_1 - ADC_VALUE_2;
  voltage_value = 3.3 * ADC_VALUE_1 /4095;
//  Serial.print("Voltage = ");
//  Serial.print(voltage_value);
//  Serial.print(" volts");
  // Update the dynamic voltage array
  for(int i=array_byte_len;i>0;i--){
    voltage_track[i]=voltage_track[i-1];
  }
  voltage_track[0]=voltage_value;

  //dvdt = PDReg(voltage_track);
  
  //Serial.println("\n");
  Serial.println(voltage_value);
  float AVG =0;
  for(int i=0; i<=array_byte_len; i++){
    AVG = AVG + voltage_track[i];
    //Serial.println(voltage_track[i]);
  }
  AVG = AVG / array_byte_len;
  //Serial.println("\n");
  //Serial.println(AVG);
  for(int i=array_byte_len; i>0; i--)
  {
    //Serial.print(voltage_track[i]-voltage_track[i-1]);
    }
  //for (int i=0; i<array_byte_len; i++) Serial.println(voltage_track[i]);
  
  // Serial.println("Differntial value is :");
  // Serial.print(differntial_value);
  // Serial.println("\n");

  /*srand(time(NULL)); 
  float val =  (float)rand()/(float)(RAND_MAX);
  */
  //char buf[16];
  //sprintf(buf, "%f", voltage_value);
  // Serial.println(voltage_value);
  // Serial.println(buf);
  // mqttClient.publish("/incitev/uc4/forecast_long_trigger", buf);

}
