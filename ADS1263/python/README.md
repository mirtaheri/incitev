
# Installations of Libraries
sudo apt-get update
sudo apt-get install ttf-wqy-zenhei
sudo apt-get install python-pip 
sudo pip install RPi.GPIO
sudo pip install spidev

# Customized information:
the code can be run in a virtualenv located in: source /home/pi/develops/incitev/bin/activate
for both c and python it is required that the SCANMODE gets set to 1 for differential case

# Useful links
https://www.waveshare.com/wiki/High-Precision_AD_HAT
https://www.waveshare.com/wiki/High-Precision_AD_HAT#Configure_interface

https://www.waveshare.com/18983.htm
##### This is NOT however ADC1263
https://github.com/waveshare/High-Precision-AD-DA-Board/tree/e831d8434e9c3112b5993fc34aceb29e6054065f/RaspberryPI/ADS1256/python3