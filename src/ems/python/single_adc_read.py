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
import paho.mqtt.client as mqtt

assert sys.version_info.major == 3 and sys.version_info.minor == 7
import time
import ADS1263
import RPi.GPIO as GPIO
import pymongo
from math import radians, cos, sin, asin, sqrt
import logging
from logging.handlers import RotatingFileHandler
from gpiozero import CPUTemperature

# ------------------------------------------------------------------------------
# -------------------- Tuning and constants settings ---------------------------
# ------------------------------------------------------------------------------



abspath = os.path.dirname(os.path.abspath(__file__))

# TODO: if no logs, create it
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
len_handler = RotatingFileHandler(abspath+'/logs.log', mode='a', maxBytes=5 * 1024 * 1024,
                                  backupCount=2, encoding=None, delay=False)
formatter = logging.Formatter('%(asctime)s : %(levelname)s : %(filename)s: %(message)s')
len_handler.setFormatter(formatter)
logger.addHandler(len_handler)
logger.info(" *** Starting service *** ")
# ----------------------------------------------------------------------------------------------------------
# ---------------------------------- constant creation and tunning section ---------------------------------
# ----------------------------------------------------------------------------------------------------------


REF = 5.08          # Modify according to actual voltage
                    # external AVDD and AVSS(Default), or internal 2.5V
TEST_ADC = 1        # ADC Test part
TEST_RTD = 0        # RTD Test part

VOLTAGE_COEFF = 1
CURRENT_COEFF = 1

# ------------------------------------------------------------------------------
# -------------------- codes for reading the registers starts here -------------
# ------------------------------------------------------------------------------

ctrl_flag = False # this can be set via an mqtt etc.
send_flag = 0
temp_controller = 0

batch_voltages = np.array([])
batch_currents = np.array([])
control_array  = np.array([])

tss=np.array([])
retention_flag = False
# temporaries
start_sampling_ts = None
end_sampling_ts = None
db_url = None
closest_tram_dist = 0

last_avg_samples = None
MOVING_AVG_LEN = 5

data =  []
batch = []

times = []
posts = []

# ATTENTION! I need to update this based on final decision, whether to consider the raw values or scaled values.
threshold = 1e-3

available_capacity = 0
ChargeProfileID    = 0

def adc_read(CONTROL=True):
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
    global MOVING_AVG_LEN
    global control_array
    global available_capacity
    global ChargeProfileID
    global threshold
    global closest_tram_dist

    voltages = np.array([])
    currents = np.array([])
 
    ocpp_smrtchg_template = {
      "csChargingProfiles": {
        "chargingProfileId": None,
        "chargingProfileKind": "Absolute",
        "chargingProfilePurpose": "TxProfile",
        "chargingSchedule": {
          "chargingRateUnit": "W",
          "chargingSchedulePeriod": [
            {
              "limit": None,
              "startPeriod": 0
            }
          ],
          "duration": None
        },
        "stackLevel": 0,
        "transactionId": None,
        "validFrom": None,
        "validTo": None
      }
    }
    
    # rate of update and size of batches
    sampling_rate = config['CONTROL']['sampling_rate']
    send_batch_size = config['CONTROL']['send_batch_size']
    raw_batch_size = config['CONTROL']['raw_batch_size']
    
    cpu = CPUTemperature()

    try:
        ADC = ADS1263.ADS1263()
        if (ADC.ADS1263_init() == -1):
            exit()
        
        logger.info("ADC are connected successfully")
        # shivid comment:
        # It doesn't work because the scanMode is not property of the Class ADS1263
        try:
            ADC.ADS1263_SetMode(1)
        except Exception as e:
            logger.erro(e)
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
            raw_current = ADC.ADS1263_GetChannalValue(1)
            # print(raw_voltage)
            # print(raw_current)

            if(raw_voltage>>31 == 1):
                voltage = REF*2 - raw_voltage * REF / 0x80000000   
            else:
                voltage = raw_voltage * REF / 0x7fffffff # 32bit
      
            if(raw_current>>31 ==1):
                current = REF*2 - raw_current * REF / 0x80000000   
            else:
                current = raw_current * REF / 0x7fffffff # 32bit
            #print(time.time()-tic)
            voltage = voltage * VOLTAGE_COEFF
            current = current * CURRENT_COEFF
            #print(voltage)
            voltages = np.append(voltages, voltage)
            currents = np.append(currents, current)
            
            # --------------------------------------------------------------------------
            # -------------------------------- CONTROL ---------------------------------
            # --------------------------------------------------------------------------
            if CONTROL:
                control_array = np.insert(control_array, 0, voltage)[:MOVING_AVG_LEN]
                
                if temp_controller == 0:
                    last_avg_samples = voltage
                    
                    
                avg_samples = control_array.sum()/len(control_array)
                rate_of_change_voltage = avg_samples - last_avg_samples
                last_avg_samples = avg_samples
                
                CONTROL_APPLIES = True if rate_of_change_voltage > threshold else False


                if CONTROL_APPLIES:
                    # make message
                    NOW = datetime.datetime.now()
                    validFrom = datetime.datetime.strftime(NOW, "%Y-%m-%dT%H:%M:%S:00+00:00")
                    validTo = datetime.datetime.strftime(NOW+datetime.timedelta(minutes=5), "%Y-%m-%dT%H:%M:%S:00+00:00")
                    message_template = copy.deepcopy(ocpp_smrtchg_template)
                    message_template['csChargingProfiles']['validFrom'] = validFrom
                    message_template['csChargingProfiles']['validTo'] = validTo
                    message_template['csChargingProfiles']['chargingProfileId'] = ChargeProfileID
               
                    
                    # from here, all depends on the received data from cscu
                    ChargeProfileID += 1 
                    if available_capacity > 0:
                        # this value should be coming from message of cscu indicating how many vehicle are connected to which chargers
                        normalized_power_per_ev = 10000
                        message_template['csChargingProfiles']['chargingSchedule']['chargingSchedulePeriod'][0]['limit'] = normalized_power_per_ev
                    else:
                        # here I need to implement discharging in case there is/are EVs but not capacity
                        # This part should be completed yet...
                        pass
                        
                    client.publish(TOPIC, json.dumps(message_template))
                    
            # --------------------------------------------------------------------------
            # --------------------------------------------------------------------------
            
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
            
            try:
                cpu_temperature = cpu.temperature
            except:
                cpu = CPUTemperature()
          
            temperature_delay = max(cpu_temperature-40, 0)/100
   
            TOTAL_DELAY = 0 #temperature_delay + 0 
            if (datetime.datetime.now().hour < 5) or (datetime.datetime.now().hour > 23):
                night_delay = 60
            else:
                night_delay = 0
                
            if closest_tram_dist <= 2:
                distance_delay = 0
            else:
                distance_delay = 1
            
            TOTAL_DELAY = temperature_delay + night_delay + distance_delay
            
            if (temp_controller%100)==0:
                url_temperature = "http://watt.linksfoundation.com:8080/api/v1/KFIk7kVivrJwWpw9pfTb/telemetry" 
                #url_sampling    = "http://watt.linksfoundation.com:8080/api/v1/YCC7kgyRvPLvbtWG9YP3/telemetry" 
                data = {"ts":time.time()*1000,
                        "values": {"temperature":cpu_temperature, "sampling":TOTAL_DELAY}}
                

                _message_to_send = json.dumps(data)
                response = requests.post(url_temperature, headers=headers, data=_message_to_send)

            #print(cpu_temperature, TOTAL_DELAY, temperature_delay, night_delay, distance_delay, closest_tram_dist)
            time.sleep(TOTAL_DELAY)

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
        logger.info("Program forced to stop")
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
                    logger.info("\n          CONNECTION ISSUE WITH SERVER")
                    retention_flag = True
                    pass
                send_flag = 0
                # temp_controller += 1
                # logger.info("I send data")
            if ctrl_flag:
                print("thread two is quitting...")
                sys.exit()
            time.sleep(1)
    except KeyboardInterrupt:
        sys.exit()
        print("intentional exit")


def tramway_positions(number_of_samples=20, valid_data_seconds=300, db_query_rate=60):
    global closest_tram_dist
    while True:
        try:
            client = pymongo.MongoClient(db_url)
            db = client["GTT"]
        
            collection_predictions = db["predictions"]
            collection_positions = db["positions"]
            
            cursor_predictions = collection_predictions.find().sort([('ExpectedArrivalTime', -1)]).limit(number_of_samples)
            cursor_positions = collection_positions.find().sort([('Timestamp', -1)]).limit(number_of_samples)
            latest_positions = list(cursor_positions)
            latest_registry = datetime.datetime(1970,1,1)
            for i in latest_positions:
                dt = datetime.datetime.strptime(i['Timestamp'].split(".")[0], "%Y-%m-%dT%H:%M:%S")
                if dt>latest_registry:
                    latest_registry = dt
                    
                    
                    
            # --------------------------- Vechile position visualization ------------------------------------
            # -----------------------------------------------------------------------------------------------
            vehicle_dict = {i['VehicleId']:i for i in latest_positions}
            
            for i in latest_positions:
                
                try:
                    var_data_time = datetime.datetime.strptime(i['Timestamp'].split(".")[0], "%Y-%m-%dT%H:%M:%S")
                    ref_data_time = datetime.datetime.strptime(vehicle_dict[i['VehicleId']]['Timestamp'].split(".")[0], "%Y-%m-%dT%H:%M:%S")
                except Exception as _err:
                    print(_err)

                if var_data_time >= ref_data_time:
                    vehicle_dict[i['VehicleId']]['Timestamp'] = i['Timestamp']
                    data = {"ts":time.time()*1000, #int(datetime.datetime.timestamp(var_data_time) * 1000),
                            "values": {"latitude": i['Latitude'], "longitude": i['Longitude'],
                                       "Speed": "N/A", "vehicleType":"tram", "vehicle":i['VehicleId'],
                                       "Line":i['PublishedLineName'], "destination": None,
                                       "StopPointName":None, "AimedArrivalTime":None,
                                       "ExpectedArrivalTime":None}}
                    
                    vehicle_dict[i['VehicleId']].update(data = data)
            

            tram_objects = ["http://watt.linksfoundation.com:8080/api/v1/TNtck3ESnADvBhfh9ggX/telemetry", 
                            "http://watt.linksfoundation.com:8080/api/v1/ZUX9YCzB1b1mtnTGiZvc/telemetry",
                            "http://watt.linksfoundation.com:8080/api/v1/Bs4NKbEb9cdaTRW0OBs1/telemetry"]
            
            
            for idx, (k, v) in enumerate(vehicle_dict.items()):
                try:
                    url_post = tram_objects[idx]

                    _message_to_send = json.dumps(v['data'])
                    response = requests.post(url_post, headers=headers, data=_message_to_send)

                except Exception as e:
                    print(idx, "I need more token for IoT platform.", e)
                    
            
            url_substation = "http://watt.linksfoundation.com:8080/api/v1/HEjtuxNwlt5sQCcQzEKe/telemetry"
            substation_fix_data = {"ts": time.time()*1000, "values": {"latitude": 45.027689409920946, "longitude": 7.639869384152541, "vehicleType": "substation"}}
            _message_to_send = json.dumps(substation_fix_data)
            response = requests.post(url_substation, headers=headers, data=_message_to_send)

            # -----------------------------------------------------------------------------------------------
            # -----------------------------------------------------------------------------------------------
                
            if (datetime.datetime.now() - latest_registry).seconds <= valid_data_seconds: # This meand if the latest data is related to more than 5 minuts ago, discard it 
                coordinates_list = coordinates(latest_positions)
                closest_tram_dist = get_distance(coordinates_list)
                
            else:
                # valid data not available
                logger.info("Databse data are related to more than 5 minutes ago; to be discarded!")
                closest_tram_dist = 2
            
        except Exception as e:
            logger.warning("CONNECTION TO DATABASE SERVER REFUSED: {}".format(e))
        
        time.sleep(db_query_rate)
      


def get_distance(lat_lon_list):
    closest_vehicle = np.inf
    for coordination in lat_lon_list:
        lat_vehicle = radians(coordination[0])
        lon_vehicle = radians(coordination[1])
        dlat = lat_vehicle - caio_mario_coordinates[0]
        dlon = lon_vehicle - caio_mario_coordinates[1]
        a = sin(dlat / 2)**2 + cos(caio_mario_coordinates[0]) * cos(lat_vehicle) * sin(dlon / 2)**2

        c = 2 * asin(sqrt(a))
        r = 6371
        if c * r < closest_vehicle:
            closest_vehicle = c*r
    return closest_vehicle


coordinates = lambda data: [(i['Latitude'], i['Longitude']) for i in data]


def stop_control():
    global ctrl_flag
    time.sleep(0.1)
    ctrl_flag = True

def read_config(file_path = abspath + "/config.yaml"):
    with open(file_path, "r") as f:
        return yaml.safe_load(f)


def onConnect(mqttc, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    if rc!=0 :
        mqttc.reconnect()
        
        
        
if __name__ == '__main__':
    config = read_config()
    # Cloud service configuration
    access_token = config['COMMUNICATION']['CLOUD']['TOKEN']
    PROTOCOL = config['COMMUNICATION']['CLOUD']['PROTOCOL']
    headers = {'Content-Type': 'application/json', }
    IP, PORT = config['COMMUNICATION']['CLOUD']['SERVER'], config['COMMUNICATION']['CLOUD']['PORT']
    url_post = '{}://{}:{}/api/v1/{}/telemetry'.format(PROTOCOL, IP, PORT, access_token)

    db_url = config['DATABASE']['DB'] + "://" + config['DATABASE']['USERNAME'] + ":" + config['DATABASE']['PASSWORD'] \
             + "@" + config['DATABASE']['HOST'] + ":" + config['DATABASE']['PORT'] + "/"
             
    caio_mario_coordinates = radians(config['METERING']['latitude']), radians(config['METERING']['longitude'])


    SETPOINT_IP, SETPOINT_PORT = config['COMMUNICATION']['SETPOINTS']['SERVER'], config['COMMUNICATION']['SETPOINTS']['PORT']
    
    TOPIC = config['COMMUNICATION']['SETPOINTS']['TOPIC']
    client               = mqtt.Client()
    client.on_connect    = onConnect
    client.connect(SETPOINT_IP, SETPOINT_PORT)

    try:
    #     threadAdcRead   = threading.Thread(target=adc_read, kwargs={"control":ctrl_flag}).start()
        AdcRead     = threading.Thread(target=adc_read).start()
        HttpWrite   = threading.Thread(target=http_write).start()
        TramTracker = threading.Thread(target=tramway_positions).start()
    #     threadprocessControl = threading.Thread(target=stop_control).start()
    except KeyboardInterrupt:
        sys.exit()
        print("intentional exit")
        
    # todo: 
    # handle disconnect from brocker
    # listening for status of the EVs from CSCU for SoC and connected vehicles
