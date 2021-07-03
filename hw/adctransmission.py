import requests
import numpy as np
import json
import datetime
import time
import threading
import copy
# import board
# import busio
# import adafruit_ads1x15.ads1015 as ADS
# from adafruit_ads1x15.analog_in import AnalogIn


access_token = ''

headers = {'Content-Type': 'application/json',}

IP, PORT =  '', ''

url_post = 'http://{}:{}/api/v1/{}/telemetry'.format(IP, PORT, access_token)



ctrl_flag = False
send_flag = 0
temp_controller = 0
batch_voltages = np.array([])

batch_voltages_bit = np.array([])

batch_voltages_bits = np.array([])
batch_currents = np.array([])

tss=np.array([])

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

    global batch_voltages_bit

    global batch_voltages_bits
    global batch_currents

    global tss
    global ctrl_flag
    global start_sampling_ts
    global end_sampling_ts

    voltages = np.array([])

    voltages_bit = np.array([])

    voltages_bits = np.array([])
    currents = np.array([])

    sampling_rate = 0.01
    send_batch_size =  100
    raw_batch_size = 100
    try:
        start_sampling_ts = 0
        while True:
            if not start_sampling_ts:
                start_sampling_ts = time.time()*1000

                
            voltages = np.append(voltages, channel_voltage.voltage)
            voltages_bit = np.append(voltages_bit, channel_voltage.value)
            #currents = np.append(currents, np.random.random())

            
            voltages = np.append(voltages, np.random.random())
            voltages_bits = np.append(voltages_bits, np.random.random())
            currents = np.append(currents, np.random.random())

            
            if len(voltages) >= raw_batch_size:
                end_sampling_ts = time.time()*1000
                tss = (np.linspace(start_sampling_ts, end_sampling_ts,
                                   int(raw_batch_size/send_batch_size))).astype(np.int64)


                batch_voltages = copy.deepcopy(voltages).reshape(-1, int(raw_batch_size/send_batch_size)).mean(axis=0)

                batch_voltages_bit = copy.deepcopy(voltages_bit).reshape(-1, int(raw_batch_size/send_batch_size)).mean(axis=0)
                send_flag = 1
                start_sampling_ts = 0
                voltages = np.array([])
                voltages_bit = np.array([])

                batch_voltages_bits = copy.deepcopy(voltages_bits).reshape(-1, int(raw_batch_size/send_batch_size)).mean(axis=0)
                batch_currents = copy.deepcopy(currents).reshape(-1, int(raw_batch_size/send_batch_size)).mean(axis=0)
                send_flag = 1
                start_sampling_ts = 0
                voltages = np.array([])
                voltages_bits = np.array([])
                currents = np.array([])

                
            time.sleep(sampling_rate)
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
    try:
        while True:
            if send_flag:
                #print(tss)
                data = [dict(ts=str(tss[i]),

                             values=dict(voltage_bit=str(batch_voltages_bit[i]),
                             voltage=str(batch_voltages[i]))) for i in range(len(batch_voltages))]

                
                    values=dict(current=str(batch_currents[i]),
                        voltage_data_bits=str(batch_voltages_bits[i]),
                        voltage=str(batch_voltages[i])))
                     for i in range(len(batch_voltages))]

                        
                _message_to_send = json.dumps(data)
                response = requests.post(url_post, headers=headers, data=_message_to_send)
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

try:
#     threadAdcRead   = threading.Thread(target=adc_read, kwargs={"control":ctrl_flag}).start()
    threadAdcRead   = threading.Thread(target=adc_read).start()
    threadHttpWrite = threading.Thread(target=http_write).start()
#     threadprocessControl = threading.Thread(target=stop_control).start()
except KeyboardInterrupt:
    sys.exit()
    print("intentional exit")
