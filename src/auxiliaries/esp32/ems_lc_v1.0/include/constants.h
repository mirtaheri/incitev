/*
ADC1:
8 channels: GPIO32 - GPIO39

ADC2:
10 channels: GPIO0, GPIO2, GPIO4, GPIO12 - GPIO15, GOIO25 - GPIO27

https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/peripherals/adc.html

*/

const int Analog_channel_pin1= 32;
const int Analog_channel_pin2= 33;
const int Analog_channel_pin3= 34;
const int Analog_channel_pin4= 35;
int ADC_VALUE_1 = 0;
int ADC_VALUE_2 = 0;
int ADC_VALUE_3 = 0;
int ADC_VALUE_4 = 0;
float voltage_value = 0; 
float differntial_value = 0;
int *ADC1_1_ADDR;
float voltage_track[10];
// 32 bits (4bytes)
float array_byte_len = sizeof(voltage_track)/4;
int DELAY = 1;

