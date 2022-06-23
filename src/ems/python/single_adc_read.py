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

VOLTAGE_COEFF = 60

abspath = os.path.dirname(os.path.abspath(__file__))


# ----- codes for reading the registers starts here ----

ctrl_flag = False # this can be set via an mqtt etc.
send_flag = 0
temp_controller = 0

batch_voltages = np.array([])
batch_currents = np.array([])

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

    voltages = np.array([])
    currents = np.array([])
 
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
            # tic = time.time()
            raw_voltage = ADC.ADS1263_GetChannalValue(0)
            rawcurrent = ADC.ADS1263_GetChannalValue(1)
            # print(raw_voltage)
            # print(rawcurrent)

            if(raw_voltage>>31 == 1):
                voltage = REF*2 - raw_voltage * REF / 0x80000000   
            else:
                voltage = raw_voltage * REF / 0x7fffffff # 32bit
      
            if(rawcurrent>>31 ==1):
                current = REF*2 - rawcurrent * REF / 0x80000000   
            else:
                current = rawcurrent * REF / 0x7fffffff # 32bit
            #print(time.time()-tic)
            voltage = voltage * VOLTAGE_COEFF
            #print(voltage)
            voltages = np.append(voltages, voltage)
            currents = np.append(currents, current)

            if len(voltages) >= int(raw_batch_size/send_batch_size): # and not retention_flag:
                end_sampling_ts = time.time() * 1000
                tss = (np.linspace(start_sampling_ts, end_sampling_ts,
                                int(raw_batch_size/send_batch_size))).astype(np.int64)
                # print("   *** AGGREGATE DATA ***")
                try:
                    batch_voltages = copy.deepcopy(voltages).reshape(-1, int(raw_batch_size/send_batch_size)).mean(axis=0)
                    batch_currents = copy.deepcopy(currents).reshape(-1, int(raw_batch_size/send_batch_size)).mean(axis=0)
                    
                except Exception as e:
                    print(e)
                # batch_of_data = adcdata[1:, :].mean(axis=0) # because first element is initialized by zeros
                # sets the flags for sending data to the cloud
                # sets the flags for sending data to the cloud
                send_flag = 1
                start_sampling_ts = 0
                voltages = np.array([])
                currents = np.array([])

            ### Teporaary part of codes and variables
            # here I control rate of change for variable of interest is changing
            # todo there should be different variables here, not only derivatives, since it can stay in critical values even in regime
            '''
            derivative_voltage = voltage - voltage_t_minus_one
            voltage_t_minus_one = voltage
            if np.abs(derivative_voltage) > 0.1: # or voltage > 630 or voltage < 560 or tram_coming:
                dynamic_sampling_time = sampling_rate
            else:
                dynamic_sampling_time = np.min((dynamic_sampling_time + sampling_rate, max_sampling_time))
            # print(dynamic_sampling_time, voltage)
            # time.sleep(dynamic_sampling_time)

            time.sleep(sampling_rate)
            '''
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
                                 current=str(batch_currents[i])))
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
