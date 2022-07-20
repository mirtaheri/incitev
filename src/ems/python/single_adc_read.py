#!/usr/bin/python
# -*- coding:utf-8 -*-


"""
This code is mainly in charge of EMS according to the OCPP architecture.
It reads the electrical measurements namely voltage and current and applies a control logic upon that.
It reads data from tramways database and also write the metering values to thingsboard database
"""

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

# ------------------------------------------------------------------------------
# -------------------- codes for reading the registers starts here -------------
# ------------------------------------------------------------------------------

ctrl_flag = False # this can be set via an mqtt etc.
send_flag = 0
temp_controller = 0

batch_voltages = np.array([])
batch_currents = np.array([])
control_array_voltage  = np.array([])
control_array_current  = np.array([])

tss=np.array([])
retention_flag = False
retention_queue = []
# temporaries
start_sampling_ts = None
end_sampling_ts = None
db_url = None
closest_tram_dist = 0

last_avg_samples = None

data =  []
batch = []

times = []
posts = []


available_capacity = 0
ChargeProfileID    = 0
control_counter = 0


def adc_read(CONTROL=True):
    """
    main function that handles the measurements and sampling and making dataset
    :param CONTROL:
    :return:
    """
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
    global control_array_voltage
    global control_array_current
    global available_capacity
    global ChargeProfileID
    global threshold
    global closest_tram_dist
    global control_counter

    voltages = np.array([])
    currents = np.array([])
    
    # template message for ocpp 2.0.1 smart charging control
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
    
    # constant for scaling the raw meaurements
    VOLTAGE_COEFF = config['METERING']['VOLTAGE_COEFF']
    CURRENT_COEFF = config['METERING']['CURRENT_COEFF']
    
    # rate of update and size of batches
    sampling_rate = config['CONTROL']['sampling_rate']
    send_batch_size = config['CONTROL']['send_batch_size']
    raw_batch_size = config['CONTROL']['raw_batch_size']
    
    
    # this number if higher, increases the effect of cpu temperature on sampling rate at cost of bigger granularity of acquired data
    SAMPLING_DIVIDER = config['CONTROL']['SAMPLING_DIVIDER']
    
    # to remove the noises
    MOVING_AVG_LEN = config['METERING']['MOVING_AVG_LEN']
    
    # ATTENTION! I need to update this based on final decision, whether to consider the raw values or scaled values.
    threshold = config['CONTROL']['THRESHOLD']
    
    
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
        
            if temp_controller%(999) == 0:
               logger.info("A regular check of adc_read for disconnection issue at cycle {} of the execution".format(temp_controller))  
            if temp_controller%(2000) == 0:
                pass
                # mqtt_client.disconnect()
                # mqtt_client.connect(SETPOINT_IP, SETPOINT_PORT)
                
            if not start_sampling_ts:
                start_sampling_ts = time.time()*1000
            # tic = time.time()
            raw_voltage = ADC.ADS1263_GetChannalValue(1)
            raw_current = ADC.ADS1263_GetChannalValue(0)

            # print(raw_voltage)
            # print(raw_current)
            if temp_controller%(999) == 0:
               logger.info("At cycle {} the raw data are : {} and {}".format(temp_controller, raw_voltage, raw_current))  
                
            try:
                if(raw_voltage>>31 == 1):
                    voltage = REF*2 - raw_voltage * REF / 0x80000000   
                else:
                    voltage = raw_voltage * REF / 0x7fffffff # 32bit
            except Exception as _e:
                logger.error("Operation on voltage data failed: {}".format(_e)) 
                
            try:
                if(raw_current>>31 ==1):
                    current = REF*2 - raw_current * REF / 0x80000000   
                else:
                    current = raw_current * REF / 0x7fffffff # 32bit  
            except Exception as _e:
                logger.error("Operation on current data failed: {}".format(_e)) 
                
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
                try:
                    # tries to filter the noises by a moving average
                    control_array_voltage = np.insert(control_array_voltage, 0, voltage)[:MOVING_AVG_LEN]
                    control_array_current = np.insert(control_array_current, 0, current)[:MOVING_AVG_LEN]
                    
                    if temp_controller == 0:
                        last_avg_samples_voltage = voltage
                        last_avg_samples_current = current
                    
                    # checks the voltage evolution
                    avg_samples_voltage = control_array_voltage.sum()/len(control_array_voltage)
                    rate_of_change_voltage = avg_samples_voltage - last_avg_samples_voltage
                    last_avg_samples_voltage = avg_samples_voltage
                    
                    # checks the current behaviour
                    avg_samples_current = control_array_current.sum()/len(control_array_current)
                    rate_of_change_current = avg_samples_current - last_avg_samples_current
                    last_avg_samples_current = avg_samples_current
                    
                    # if voltage is increasing and the current is reducing, there is a braking event
                    CONTROL_APPLIES = True if rate_of_change_voltage > threshold and np.sign(rate_of_change_current) == -1 else False
                except Exception as err:
                    print("Control application issue: ".format(err))
                    logger.error("Control application issue: ".format(err))


                if CONTROL_APPLIES:
                    # make message
                    logger.info("Control application: {}".format(rate_of_change_voltage))
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
                    
                    if temp_controller - control_counter > 60:
                        control_counter = temp_controller
                        try:
                            mqtt_client.publish(TOPIC, json.dumps(message_template))
                            logger.info("Control is set.")
                        except Exception as e_pub:
                            print("OCPP setpoint instruction faced issue: {}".format(e_pub))
                            logger.error("OCPP setpoint instruction faced issue: {}".format(e_pub))

            # --------------------------------------------------------------------------
            # --------------------------------------------------------------------------
            if temp_controller%(999) == 0:
               logger.info("A regular check for disconnection issue; voltage array length is: {}".format(voltages.size))   
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
            
            # this value of 300 is put based on experience and some tries. I need to watch the temperature of cpu on dashboard and change this accordingly to avoid overheating RPI
            # makes a delay proportional to the temperature of CPU
            temperature_delay = max(cpu_temperature-40, 0)/SAMPLING_DIVIDER
            
            # if there is valid data comming from tramways, sets the delay inversely proportional to the closest tramways
            if closest_tram_dist <= 2:
                distance_delay = 0
            else:
                distance_delay = 1
            
            # if night, slow down sampling
            if (datetime.datetime.now().hour < 5) or (datetime.datetime.now().hour >= 22):
                night_delay = 10
                distance_delay = 0
                temperature_delay = 0
            else:
                night_delay = 0

            
            TOTAL_DELAY = temperature_delay + night_delay + distance_delay
            
            if (temp_controller%100)==0:
                url_temperature = "http://watt.linksfoundation.com:8080/api/v1/KFIk7kVivrJwWpw9pfTb/telemetry" 
                #url_sampling    = "http://watt.linksfoundation.com:8080/api/v1/YCC7kgyRvPLvbtWG9YP3/telemetry" 
                data = {"ts":time.time()*1000,
                        "values": {"temperature":cpu_temperature, "sampling":TOTAL_DELAY}}
                

                _message_to_send = json.dumps(data)
                try:
                    response_temperature = requests.post(url_temperature, headers=headers, data=_message_to_send, timeout=3)
                except Exception as e:
                    logger.info("Temperature update failed: {}".format(response_temperature))
                    
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
    """
    sends data over http to the cloud service (thingsboard)
    :return:
    """
    global temp_controller
    global send_flag
    global ctrl_flag
    global data
    global retention_flag
    global retention_queue

    try:
        while True:
            if temp_controller%(999) == 0:
                logger.info("At cycle {} the http_write thread is alive".format(temp_controller))  
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
                    response_metering = requests.post(url_post, headers=headers, data=_message_to_send, timeout=5)
                    # print(" -----> ", response.ok, response, " <------")
                    logger.info("Latest buffered data are POSTed to server successfully with response {}".format(response_metering))
                    retention_flag = False
                except Exception as e:
                    logger.error("Connection to server problem : {}".format(e))
                    retention_flag = True
                    retention_queue.append(_message_to_send)

                # reset the flag to let control loop fill buffer again
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



def retention():

    global retention_flag
    global retention_queue
    
    while True:
        RETENTION_FAILURES = 0
        logger.info("There are {} queued message at buffer.".format(len(retention_queue)))
        #retry for sending again data that remained in retention queue
        for msg_idx in range(len(retention_queue)):
            try:
                response_retry = requests.post(url_post, headers=headers, data=retention_queue[msg_idx], timeout=4)
                if response_retry.ok:
                    logger.info("Successfully pushed the data with index {}.".format(msg_idx))
                    retention_queue.pop(msg_idx)
            except Exception as e:
                logger.error("New attempt for sending data failed again: {}".format(e))
                RETENTION_FAILURES += 1
            
            # if attempts are failing all, better to wait   
            if RETENTION_FAILURES > 3:
                break
                
        time.sleep(120)





def tramway_positions(number_of_samples=20, valid_data_seconds=300, db_query_rate=60, GW_POS_SEND=False):
    """
    makes query to database and gets the latest data of tramways fleet
    :param number_of_samples: int
        number of latest documents
    :param valid_data_seconds: int
        more than this, already data is obsolete
    :param db_query_rate: int
        delay between queries
    :return:
    """
    global closest_tram_dist
    while True:
        MONGO_CONNECTED = True
        try:
            # connect o DB
            db_client = pymongo.MongoClient(db_url)
            db = db_client["GTT"]

            # tabels
            collection_predictions = db["predictions"]
            collection_positions = db["positions"]
            
            # separate cursors per table
            cursor_predictions = collection_predictions.find().sort([('ExpectedArrivalTime', -1)]).limit(number_of_samples)
            cursor_positions = collection_positions.find().sort([('Timestamp', -1)]).limit(number_of_samples)
            
        except Exception as e:
            MONGO_CONNECTED = False
            logger.error("CONNECTION TO DATABASE SERVER REFUSED: {}".format(e))
            print("CONNECTION TO DATABASE SERVER REFUSED: {}".format(e))
            time.sleep(db_query_rate)
        
        if MONGO_CONNECTED == True:
            try:                
                latest_positions = list(cursor_positions)
                latest_registry = datetime.datetime(1970,1,1)
                for i in latest_positions:
                    dt = datetime.datetime.strptime(i['Timestamp'].split(".")[0], "%Y-%m-%dT%H:%M:%S")
                    if dt>latest_registry:
                        latest_registry = dt
            except Exception as e:
                logger.error("error while parsing data: {}".format(e))
                
                    
            # --------------------------- Vechile position visualization ------------------------------------
            # -----------------------------------------------------------------------------------------------
            # template dictionary for vehicles data
            if GW_POS_SEND:
                vehicle_dict = {i['VehicleId']:i for i in latest_positions}
                
                for i in latest_positions:
                    
                    try:
                        # compare the most recent data per tramway
                        var_data_time = datetime.datetime.strptime(i['Timestamp'].split(".")[0], "%Y-%m-%dT%H:%M:%S")
                        ref_data_time = datetime.datetime.strptime(vehicle_dict[i['VehicleId']]['Timestamp'].split(".")[0], "%Y-%m-%dT%H:%M:%S")
                    except Exception as _err:
                        logger.error(_err)
    
                    if var_data_time >= ref_data_time:
                        vehicle_dict[i['VehicleId']]['Timestamp'] = i['Timestamp']
                        # In fact I need to put the timestamp of the latest retreived data from database. But now
                        # DB doesn't get updated frequently and this maight be longer the interval thingsboard dashboard
                        # keeps visualization of latest device data
                        data = {"ts":time.time()*1000, #int(datetime.datetime.timestamp(var_data_time) * 1000),
                                "values": {"latitude": i['Latitude'], "longitude": i['Longitude'],
                                           "Speed": "N/A", "vehicleType":"tram", "vehicleID":i['VehicleId'],
                                           "Line":i['PublishedLineName'], "destination": None,
                                           "StopPointName":None, "AimedArrivalTime":None,
                                           "ExpectedArrivalTime":None}}
                        
                        vehicle_dict[i['VehicleId']].update(data = data)
                
                # I can add as much as needed, however on map becomes confusing
                tram_objects = ["http://watt.linksfoundation.com:8080/api/v1/TNtck3ESnADvBhfh9ggX/telemetry", 
                                "http://watt.linksfoundation.com:8080/api/v1/ZUX9YCzB1b1mtnTGiZvc/telemetry",
                                "http://watt.linksfoundation.com:8080/api/v1/Bs4NKbEb9cdaTRW0OBs1/telemetry",
                                "http://watt.linksfoundation.com:8080/api/v1/DLtQl9FdEmJlD5hWpsoE/telemetry",
                                "http://watt.linksfoundation.com:8080/api/v1/TBfqqRrI3g6eILG4EKms/telemetry",
                                "http://watt.linksfoundation.com:8080/api/v1/S1VwR9v83PPLiGj4QqOg/telemetry"]
                
                # sends the latest positions of the tramways fleet to thingsboard for visualization
                for idx, (k, v) in enumerate(vehicle_dict.items()):
                    try:
                        url_post = tram_objects[idx]
    
                        _message_to_send = json.dumps(v['data'])
                        response_fleet = requests.post(url_post, headers=headers, data=_message_to_send)
    
                    except Exception as e:
                        print(idx, "I need more token for IoT platform.", e)
                        logger.error("More token for IoT platform needed : {}".format(e))
                        
                        
            # -----------------------------------------------------------------------------------------------
            # -----------------------------------------------------------------------------------------------
            try:
                db_client.close()                
            except Exception as e:
                logger.error("Issue while closing connection to DB {}".format(e))
                
            if (datetime.datetime.now() - latest_registry).seconds <= valid_data_seconds: # This meand if the latest data is related to more than 5 minuts ago, discard it     
                try:
                    coordinates_list = coordinates(latest_positions)
                    closest_tram_dist = get_distance(coordinates_list)
                except Exception as e:
                    logger.error("Calculation erro {}".format(e))
            else:
                # valid data not available
                # logger.info("Databse data are related to more than 5 minutes ago; to be discarded!")
                closest_tram_dist = 2
                

            # -----------------------------------------------------------------------------------------------
            # -----------------------------------------------------------------------------------------------
            # for visualization of the substation position on map
            try:
                url_substation = "http://watt.linksfoundation.com:8080/api/v1/HEjtuxNwlt5sQCcQzEKe/telemetry"
                substation_fix_data = {"ts": time.time()*1000, "values": {"latitude": 45.027689409920946, "longitude": 7.639869384152541, "vehicleType": "substation"}}
                _message_to_send = json.dumps(substation_fix_data)
                response_station = requests.post(url_substation, headers=headers, data=_message_to_send, timeout=10)
                logger.info("Substation position is set successfully")
            
            except Exception as e:
                time.sleep(db_query_rate)
                logger.error("Substation position set is failed {}".format(e))
                continue

        logger.info("Positioning service finished a loop.")
        time.sleep(db_query_rate)
      
      
      
      

def get_distance(lat_lon_list):
    """
    calculated the distance between two points (substation and the closest tramway)
    :param lat_lon_list: list of tuples indicating the latest positions of tramways fleet
    :return:
    """
    closest_vehicle = np.inf
    for coordination in lat_lon_list:
        lat_vehicle = radians(coordination[0])
        lon_vehicle = radians(coordination[1])
        dlat = lat_vehicle - caio_mario_coordinates[0]
        dlon = lon_vehicle - caio_mario_coordinates[1]
        a = sin(dlat / 2)**2 + cos(caio_mario_coordinates[0]) * cos(lat_vehicle) * sin(dlon / 2)**2

        c = 2 * asin(sqrt(a))
        # earth diameter
        r = 6371
        if c * r < closest_vehicle:
            closest_vehicle = c*r
    return closest_vehicle

# auxiliary function
coordinates = lambda data: [(i['Latitude'], i['Longitude']) for i in data]



def stop_control():
    """
    to listen and get execution control from external components
    :return:
    """
    global ctrl_flag
    time.sleep(0.1)
    ctrl_flag = True



def read_config(file_path = abspath + "/config.yaml"):
    """
    read configuration file
    :param file_path:
    :return:
    """
    with open(file_path, "r") as f:
        return yaml.safe_load(f)



def onConnect(mqttc, userdata, flags, rc):
    """
    mqtt calback
    :param mqttc:
    :param userdata:
    :param flags:
    :param rc:
    :return:
    """
    print("Connected with result code "+str(rc))
    if rc!=0 :
        mqttc.reconnect()
        
        
        
if __name__ == '__main__':

    # read configuration file
    config = read_config()

    # Cloud service configuration
    access_token = config['COMMUNICATION']['CLOUD']['TOKEN']
    PROTOCOL = config['COMMUNICATION']['CLOUD']['PROTOCOL']
    headers = {'Content-Type': 'application/json', }
    IP, PORT = config['COMMUNICATION']['CLOUD']['SERVER'], config['COMMUNICATION']['CLOUD']['PORT']
    url_post = '{}://{}:{}/api/v1/{}/telemetry'.format(PROTOCOL, IP, PORT, access_token)

    # make the url for thingsboard instance on watt
    db_url = config['DATABASE']['DB'] + "://" + config['DATABASE']['USERNAME'] + ":" + config['DATABASE']['PASSWORD'] \
             + "@" + config['DATABASE']['HOST'] + ":" + config['DATABASE']['PORT'] + "/"
             
    # to be used for measuring distance of tramways and also for visualization on dashboard
    caio_mario_coordinates = radians(config['METERING']['latitude']), radians(config['METERING']['longitude'])

    # connection to cscu and setpoints communication via mqtt
    SETPOINT_IP, SETPOINT_PORT = config['COMMUNICATION']['SETPOINTS']['SERVER'], config['COMMUNICATION']['SETPOINTS']['PORT']
    
    TOPIC = config['COMMUNICATION']['SETPOINTS']['TOPIC']
    mqtt_client               = mqtt.Client()
    mqtt_client.on_connect    = onConnect
    mqtt_client.connect(SETPOINT_IP, SETPOINT_PORT)

    #TODO: I need to set a listener to cscu for state of connected vehicles and their parameters

    try:
        # handle differnt parts of codes by different separated threads
        # threadAdcRead   = threading.Thread(target=adc_read, kwargs={"control":ctrl_flag}).start()
        
        # This is the main thread that handles the measurement and control loop
        AdcRead     = threading.Thread(target=adc_read).start()
        
        # This thread is in charge of sending batch data to database
        HttpWrite   = threading.Thread(target=http_write).start()
        
        # This thread is only for making regular query to tramways database
        TramTracker = threading.Thread(target=tramway_positions).start()
        
        # This thread is only for making regular query to tramways database
        DataRetention = threading.Thread(target=retention).start()
        # threadprocessControl = threading.Thread(target=stop_control).start()
        
    except KeyboardInterrupt:
        logger.warning("Forced exit by user interface")
        print("Forced exit by user interface")
        sys.exit()        
    # todo: 
    # handle disconnect from broker
    # listening for status of the EVs from CSCU for SoC and connected vehicles
