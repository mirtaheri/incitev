#!/usr/bin/python
# -*- coding:utf-8 -*-
import requests
import numpy as np
import json
import datetime
import threading
import copy
import sys, os
import yaml

assert sys.version_info.major == 3 and sys.version_info.minor == 7
import time
import ADS1263
import RPi.GPIO as GPIO

REF = 5.08          # Modify according to actual voltage
                    # external AVDD and AVSS(Default), or internal 2.5V
TEST_ADC = 1        # ADC Test part
TEST_RTD = 0        # RTD Test part


abspath = os.path.dirname(os.path.abspath(__file__))


# ----- codes for reading the registers starts here ----

ctrl_flag = False # this can be set via an mqtt etc.
send_flag = 0
temp_controller = 0

batch_voltages = np.array([])
batch_voltages_bits = np.array([])
batch_currents = np.array([])


batch_var3 = np.array([])
batch_var4 = np.array([])
batch_var5 = np.array([])
batch_var6 = np.array([])
batch_var7 = np.array([])
batch_var8 = np.array([])
batch_var9 = np.array([])
batch_var10 = np.array([])

tss=np.array([])
retention_flag = False
# temporaries
start_sampling_ts = None
end_sampling_ts = None
data =  []
batch = []

times = []
posts = []

def adc_read():
    global send_flag
    global temp_controller
    global times
    global posts
    global batch_voltages
    global batch_voltages_bits
    global batch_currents
    global tss
    global ctrl_flag
    global start_sampling_ts
    global end_sampling_ts
    
    global batch_var3
    global batch_var4
    global batch_var5
    global batch_var6
    global batch_var7
    global batch_var8
    global batch_var9
    global batch_var10

    voltages = np.array([])
    currents = np.array([])
    
    var_3s = np.array([])
    var_4s = np.array([]) 
    var_5s = np.array([]) 
    var_6s = np.array([]) 
    var_7s = np.array([]) 
    var_8s = np.array([]) 
    var_9s = np.array([]) 
    var_10s = np.array([])  
    # rate of update and size of batches
    sampling_rate = config['CONTROL']['sampling_rate']
    send_batch_size = config['CONTROL']['send_batch_size']
    raw_batch_size = config['CONTROL']['raw_batch_size']

    try:
        ADC = ADS1263.ADS1263()
        if (ADC.ADS1263_init() == -1):
            exit()
            
        # shivid comment:
        # It doesn't work because the scanMode is not property of the Class ADS1263
        try:
            ADC.ADS1263_SetMode(1)
        except Exception as e:
            print(e)
        # ADC.ADS1263_DAC_Test(1, 1)      # Open IN6
        # ADC.ADS1263_DAC_Test(0, 1)      # Open IN7
        
        voltage_t_minus_one = 0
        start_sampling_ts = 0
        max_sampling_time = sampling_rate * 50
        dynamic_sampling_time = max_sampling_time
        # this data will come from a forecast routine tha observes data of 5T
        tram_coming = 0

        adcdata = np.zeros(shape=(5))

        while(1):
    
            if not start_sampling_ts:
                start_sampling_ts = time.time()*1000

            if(TEST_ADC):       # ADC Test
                tic = time.time()
                ADC_Value = ADC.ADS1263_GetAll()    # get ADC1 value
                #adcdata = np.vstack((adcdata, ADC_Value[:5]))
                #print(np.array(ADC_Value)/0x7fffffff)
                raw_voltage = ADC_Value[0]
                rawcurrent = ADC_Value[1]
                
                
                var_3 = ADC_Value[2]
                var_4 = ADC_Value[3]
                var_5 = ADC_Value[4]
                var_6 = ADC_Value[5]
                var_7 = ADC_Value[6]
                var_8 = ADC_Value[7]
                var_9 = ADC_Value[8]
                var_10 = ADC_Value[9]
                if raw_voltage >= 0x7fffffff:
                    hex_value = raw_voltage
                    
                temp_var_10 = raw_voltage>>31   
                
                if(raw_voltage>>31 == 1):
                    voltage = REF*2 - raw_voltage * REF / 0x80000000   
                else:
                    voltage = raw_voltage * REF / 0x7fffffff # 32bit
                
                if(rawcurrent>>31 ==1):
                    current = REF*2 - rawcurrent * REF / 0x80000000   
                else:
                    current = rawcurrent * REF / 0x7fffffff # 32bit
                print(time.time()-tic)  
                
                if(var_3>>31 ==1):
                    temp_var_3 = var_3 / 0x80000000
                else:
                    temp_var_3 = var_3 /0x7fffffff  # 32bit
                
                if(var_4>>31 ==1):
                    temp_var_4 = var_4 / 0x80000000
                else:
                    temp_var_4 = var_4 /0x7fffffff  # 32bit
                
                if(var_5>>31 ==1):
                    temp_var_5 = var_5 / 0x80000000
                else:
                    temp_var_5 = var_5 /0x7fffffff  # 32bit
                    
                if(var_6>>31 ==1):
                    temp_var_6 = var_6 / 0x80000000
                else:
                    temp_var_6 = var_6 /0x7fffffff  # 32bit
                
                if(var_7>>31 ==1):
                    temp_var_7 = var_7 / 0x80000000
                else:
                    temp_var_7 = var_7 /0x7fffffff  # 32bit
                    
                if(var_8>>31 ==1):
                    temp_var_8 = var_8 / 0x80000000
                else:
                    temp_var_8 = var_8 /0x7fffffff  # 32bit
                    
                if(var_9>>31 ==1):
                    temp_var_9 = var_9 / 0x80000000
                else:
                    temp_var_9 = var_9 /0x7fffffff  # 32bit
                    
                # if(var_10>>31 ==1):
                    # temp_var_10 = var_10 / 0x80000000
                # else:
                    # temp_var_10 = var_10 /0x7fffffff  # 32bit
    
                voltages = np.append(voltages, voltage)
                currents = np.append(currents, current)
                
                var_3s = np.append(var_3s, temp_var_3)
                var_4s = np.append(var_4s, temp_var_4)
                var_5s = np.append(var_5s, temp_var_5)
                var_6s = np.append(var_6s, temp_var_6)
                var_7s = np.append(var_7s, temp_var_7)
                var_8s = np.append(var_8s, temp_var_8)
                var_9s = np.append(var_9s, temp_var_9)
                var_10s= np.append(var_10s, temp_var_10)
                



                if len(voltages) >= int(raw_batch_size/send_batch_size): # and not retention_flag:
                    end_sampling_ts = time.time() * 1000
                    tss = (np.linspace(start_sampling_ts, end_sampling_ts,
                                    int(raw_batch_size/send_batch_size))).astype(np.int64)
                    # print("   *** AGGREGATE DATA ***")
                    try:
                        batch_voltages = copy.deepcopy(voltages).reshape(-1, int(raw_batch_size/send_batch_size)).mean(axis=0)
                        batch_currents = copy.deepcopy(currents).reshape(-1, int(raw_batch_size/send_batch_size)).mean(axis=0)
                        
                        
                        batch_var3 = copy.deepcopy(var_3s).reshape(-1, int(raw_batch_size/send_batch_size)).mean(axis=0)
                        batch_var4 = copy.deepcopy(var_4s).reshape(-1, int(raw_batch_size/send_batch_size)).mean(axis=0)
                        batch_var5 = copy.deepcopy(var_5s).reshape(-1, int(raw_batch_size/send_batch_size)).mean(axis=0)
                        batch_var6 = copy.deepcopy(var_6s).reshape(-1, int(raw_batch_size/send_batch_size)).mean(axis=0)
                        batch_var7 = copy.deepcopy(var_7s).reshape(-1, int(raw_batch_size/send_batch_size)).mean(axis=0)
                        batch_var8 = copy.deepcopy(var_8s).reshape(-1, int(raw_batch_size/send_batch_size)).mean(axis=0)
                        batch_var9 = copy.deepcopy(var_9s).reshape(-1, int(raw_batch_size/send_batch_size)).mean(axis=0)
                        batch_var10 = copy.deepcopy(var_10s).reshape(-1, int(raw_batch_size/send_batch_size)).mean(axis=0)
                        
                    except Exception as e:
                        print(e)
                    # batch_of_data = adcdata[1:, :].mean(axis=0) # because first element is initialized by zeros
                    # sets the flags for sending data to the cloud
                    # sets the flags for sending data to the cloud
                    send_flag = 1
                    start_sampling_ts = 0
                    voltages = np.array([])
                    currents = np.array([])


                    var_3s = np.array([])
                    var_4s = np.array([]) 
                    var_5s = np.array([]) 
                    var_6s = np.array([]) 
                    var_7s = np.array([]) 
                    var_8s = np.array([]) 
                    var_9s = np.array([]) 
                    var_10s = np.array([])  
    
                ### Teporaary part of codes and variables
                # here I control rate of change for variable of interest is changing
                # todo there should be different variables here, not only derivatives, since it can stay in critical values even in regime
                
                derivative_voltage = voltage - voltage_t_minus_one
                voltage_t_minus_one = voltage
                if np.abs(derivative_voltage) > 0.1: # or voltage > 630 or voltage < 560 or tram_coming:
                    dynamic_sampling_time = sampling_rate
                else:
                    dynamic_sampling_time = np.min((dynamic_sampling_time + sampling_rate, max_sampling_time))
                # print(dynamic_sampling_time, voltage)
                # time.sleep(dynamic_sampling_time)

                time.sleep(sampling_rate)
                temp_controller += 1
                if ctrl_flag:
                    print("thread one is quitting...")
                    sys.exit()

                """
                for i in range(0, 10):
                    if(ADC_Value[i]>>31 ==1):
                        print("ADC1 IN%d = -%lf" %(i, (REF*2 - ADC_Value[i] * REF / 0x80000000)))  
                        
                    else:
                        print("ADC1 IN%d = %lf" %(i, (ADC_Value[i] * REF / 0x7fffffff)))   # 32bit

                print("\33[12A")
                """

            elif(TEST_RTD):     # RTD Test
                ADC_Value = ADC.ADS1263_RTD_Test()
                RES = ADC_Value / 2147483647.0 * 2.0 *2000.0       #2000.0 -- 2000R, 2.0 -- 2*i
                print("RES is %lf"%RES)
                TEMP = (RES/100.0 - 1.0) / 0.00385      #0.00385 -- pt100
                print("TEMP is %lf"%TEMP)
                print("\33[3A")

    except IOError as e:
        print(e)
    
    except KeyboardInterrupt:
        print("ctrl + c:")
        print("Program end")
        ADC.ADS1263_Exit()
        exit()


def http_write():
    global temp_controller
    global send_flag
    global ctrl_flag
    global data
    global retention_flag

    try:
        while True:
            if send_flag:
                #data = [dict(ts=str(tss[i]), values=dict(voltage=str(batch_voltages[i]), current=str(batch_currents[i]))) for i in range(len(batch_voltages))]
                
                data = [dict(ts=str(tss[i]), 
                              values=dict(
                                 voltage=str(batch_voltages[i]),
                                 current=str(batch_currents[i]),
                                 var3=str(batch_var3[i]),
                                 var4=str(batch_var4[i]),
                                 var5=str(batch_var5[i]),
                                 var6=str(batch_var6[i]),
                                 var7=str(batch_var7[i]),
                                 var8=str(batch_var8[i]),
                                 var9=str(batch_var9[i]),
                                 var10=str(batch_var10[i])))
                              for i in range(len(batch_voltages))]
                
                #print(data)
                _message_to_send = json.dumps(data)
                try:
                    response = requests.post(url_post, headers=headers, data=_message_to_send)
                    retention_flag = False
                except:
                    print("\n          CONNECTION ISSUE WITH SERVER")
                    retention_flag = True
                    pass
                send_flag = 0
                temp_controller += 1
                print("I send data")
            if ctrl_flag:
                print("thread two is quitting...")
                sys.exit()
    except KeyboardInterrupt:
        sys.exit()
        print("intentional exit")


def stop_control():
    global ctrl_flag
    time.sleep(0.1)
    ctrl_flag = True

def read_config(file_path = abspath + "/config.yaml"):
    with open(file_path, "r") as f:
        return yaml.safe_load(f)


if __name__ == '__main__':
    config = read_config()
    # Cloud service configuration
    access_token = config['COMMUNICATION']['CLOUD']['TOKEN']
    PROTOCOL = config['COMMUNICATION']['CLOUD']['PROTOCOL']
    headers = {'Content-Type': 'application/json', }
    IP, PORT = config['COMMUNICATION']['CLOUD']['SERVER'], config['COMMUNICATION']['CLOUD']['PORT']
    url_post = '{}://{}:{}/api/v1/{}/telemetry'.format(PROTOCOL, IP, PORT, access_token)
    
    try:
    #     threadAdcRead   = threading.Thread(target=adc_read, kwargs={"control":ctrl_flag}).start()
        threadAdcRead   = threading.Thread(target=adc_read).start()
        threadHttpWrite = threading.Thread(target=http_write).start()
    #     threadprocessControl = threading.Thread(target=stop_control).start()
    except KeyboardInterrupt:
        sys.exit()
        print("intentional exit")
