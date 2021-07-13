import requests
import numpy as np
import json
import datetime
import time
import threading
import copy
import sys, os

assert sys.version_info.major == 3 and sys.version_info.minor == 8
import yaml

try:
    import board
    import busio
    import adafruit_ads1x15.ads1015 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn
    device = True

except:
    print("\n   *** You do not have installed the required  libraries to get data from the ADC... Switching to remote device mode ****  \n")
    device = False


abspath = os.path.dirname(os.path.abspath(__file__))

# GLOBAL VARIABLES

ctrl_flag = False # this can be set via an mqtt etc.
send_flag = 0
temp_controller = 0
# These are the data batches for temporary data collections
batch_voltages = np.array([])
batch_voltages_bits = np.array([])
batch_currents = np.array([])
# Timestamps related to the monitored data
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
    voltages_bits = np.array([])
    currents = np.array([])
    # rate of update and size of batches
    sampling_rate = config['CONTROL']['sampling_rate']
    send_batch_size = config['CONTROL']['send_batch_size']
    raw_batch_size = config['CONTROL']['raw_batch_size']

    try:
        voltage_t_minus_one = 0
        start_sampling_ts = 0
        max_sampling_time = sampling_rate * 50
        dynamic_sampling_time = max_sampling_time
        # this data will come from a forecast routine tha observes data of 5T
        tram_coming = 0
        while True:
            # start_sampling_ts is used for only controlling logic
            if not start_sampling_ts:
                start_sampling_ts = time.time()*1000

            # if it is running on test system, or field device
            if device:
                voltage = channel_voltage.voltage
                voltage_bits = channel_voltage.value
            else:
                voltage = np.random.normal(loc=600.0, scale=10, size=None)
                voltage_bits = np.random.normal(loc=256.0, scale=1, size=None)

            voltages = np.append(voltages, voltage)
            voltages_bits = np.append(voltages_bits, voltage_bits)
            currents = np.append(currents, np.abs(np.random.normal(loc=0, scale=100, size=None)))

            if len(voltages) >= raw_batch_size: # and not retention_flag:
                end_sampling_ts = time.time() * 1000
                tss = (np.linspace(start_sampling_ts, end_sampling_ts,
                                   int(raw_batch_size/send_batch_size))).astype(np.int64)

                batch_voltages = copy.deepcopy(voltages).reshape(-1, int(raw_batch_size/send_batch_size)).mean(axis=0)
                batch_voltages_bits = copy.deepcopy(voltages_bits).reshape(-1, int(raw_batch_size/send_batch_size)).mean(axis=0)
                batch_currents = copy.deepcopy(currents).reshape(-1, int(raw_batch_size/send_batch_size)).mean(axis=0)

                # sets the flags for sending data to the cloud
                send_flag = 1
                start_sampling_ts = 0
                voltages = np.array([])
                voltages_bits = np.array([])
                currents = np.array([])

            ### Teporaary part of codes and variables
            # here I control rate of change for variable of interest is changing
            # todo there should be different variables here, not only derivatives, since it can stay in critical values even in regime
            derivative_voltage = voltage - voltage_t_minus_one
            voltage_t_minus_one = voltage
            if np.abs(derivative_voltage) > 30 or voltage > 630 or voltage < 560 or tram_coming:
                dynamic_sampling_time = sampling_rate
            else:
                dynamic_sampling_time = np.min((dynamic_sampling_time + 0.01, max_sampling_time))

            time.sleep(dynamic_sampling_time)
            temp_controller += 1
            if ctrl_flag:
                print("thread one is quitting...")
                sys.exit()
    except KeyboardInterrupt:
        sys.exit()
        print("intentional exit")

def http_write():
    global temp_controller
    global send_flag
    global ctrl_flag
    global data
    global retention_flag

    try:
        while True:
            if send_flag:
                
                data = [dict(ts=str(tss[i]), values=dict(current=str(batch_currents[i]), voltage_data_bits=str(batch_voltages_bits[i]), voltage=str(batch_voltages[i]))) for i in range(len(batch_voltages))]

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

    if device:
        # ADC drive configuration
        i2c = busio.I2C(board.SCL, board.SDA)
        ads = ADS.ADS1015(i2c)
        channel_voltage = AnalogIn(ads, ADS.P0, ADS.P1)

    try:
    #     threadAdcRead   = threading.Thread(target=adc_read, kwargs={"control":ctrl_flag}).start()
        threadAdcRead   = threading.Thread(target=adc_read).start()
        threadHttpWrite = threading.Thread(target=http_write).start()
    #     threadprocessControl = threading.Thread(target=stop_control).start()
    except KeyboardInterrupt:
        sys.exit()
        print("intentional exit")
