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

abspath = os.path.dirname(os.path.abspath(__file__))


try:
    import board
    import busio
    import adafruit_ads1x15.ads1015 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn
    device = True

except:
    print("\n   *** You do not have installed the required  libraries to get data from the ADC... Switching to remote device mode ****  \n")
    device = False



class Metering:

    def __init__(self, conf_path):
        self.voltages = np.array([])
        self.batch_voltages_bits = np.array([])
        self.batch_currents = np.array([])
        self.tss = np.array([])

        self.voltages = np.array([])
        self.voltages_bits = np.array([])
        self.currents = np.array([])

        self.conf_path = conf_path


    def adc_read(self):
        sampling_rate = self.config['CONTROL']['sampling_rate']
        send_batch_size = self.config['CONTROL']['send_batch_size']
        raw_batch_size = self.config['CONTROL']['raw_batch_size']
        try:
            start_sampling_ts = 0
            while True:
                # start_sampling_ts is used for only controlling logic
                if not start_sampling_ts:
                    start_sampling_ts = time.time() * 1000

                # if it is running on test system, or field device
                # I then use here fo adding as much as variable I need
                if device:
                    voltages = np.append(voltages, self.channel_voltage.voltage)
                    voltages_bits = np.append(voltages_bits, self.channel_voltage.value)
                else:
                    voltages = np.append(voltages, np.random.random())
                    voltages_bits = np.append(voltages_bits, np.random.random())
                currents = np.append(currents, np.random.random())

                #
                if len(voltages) >= raw_batch_size: # and not retention_flag:
                    end_sampling_ts = time.time()*1000
                    # array of
                    tss = (np.linspace(start_sampling_ts, end_sampling_ts,
                                       int(raw_batch_size/send_batch_size))).astype(np.int64)

                batch_voltages = copy.deepcopy(voltages).reshape(-1, int(raw_batch_size/send_batch_size)).mean(axis=0)
                batch_voltages_bits = copy.deepcopy(voltages_bits).reshape(-1, int(raw_batch_size/send_batch_size)).mean(axis=0)
                batch_currents = copy.deepcopy(currents).reshape(-1, int(raw_batch_size/send_batch_size)).mean(axis=0)

        except KeyboardInterrupt:
            sys.exit()
            print("intentional exit")

    def http_write(self):
        pass

    def run(self):
        with open(self.conf_path, "r") as f:
            self.config = yaml.safe_load(f)
        # Cloud service configuration
        access_token = self.config['COMMUNICATION']['CLOUD']['TOKEN']
        PROTOCOL = self.config['COMMUNICATION']['CLOUD']['PROTOCOL']
        headers = {'Content-Type': 'application/json', }
        IP, PORT = self.config['COMMUNICATION']['CLOUD']['SERVER'], self.config['COMMUNICATION']['CLOUD']['PORT']
        url_post = '{}://{}:{}/api/v1/{}/telemetry'.format(PROTOCOL, IP, PORT, access_token)
        if device:
            # ADC drive configuration
            i2c = busio.I2C(board.SCL, board.SDA)
            ads = ADS.ADS1015(i2c)
            #
            self.channel_voltage = AnalogIn(ads, ADS.P0, ADS.P1)

        try:
            threading.Thread(target=self.adc_read).start()
            threading.Thread(target=self.http_write).start()

        except KeyboardInterrupt:
            sys.exit()
            print("intentional exit")

if __name__ == '__main__':


    mo = Metering(abspath + "/config.yaml")
    mo.run()
