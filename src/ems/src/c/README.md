# Installations of Libraries

## Install BCM2835 libraries

wget http://www.airspayce.com/mikem/bcm2835/bcm2835-1.64.tar.gz
tar zxvf bcm2835-1.64.tar.gz 
cd bcm2835-1.64/
sudo ./configure
sudo make
sudo make check
sudo make install

## Install WiringPi libraries
sudo apt-get install wiringpi
cd /tmp
wget https://project-downloads.drogon.net/wiringpi-latest.deb
sudo dpkg -i wiringpi-latest.deb

gpio -v
**You will get 2.52 information if you install it correctly**

### to test and run the code:
cd /path/to/the/code
./main


# Compile code (if any code in path)
sudo make clean
sudo make

# Demo code
sudo apt-get install p7zip-full
wget http://www.waveshare.com/w/upload/6/64/High-Pricision_AD_HAT_Code.7z
7z x High-Pricision_AD_HAT_Code.7z -r -o./High-Pricision_AD_HAT_Code
cd High-Pricision_AD_HAT_Code/

## compile them
cd ~/High-Pricision_AD_HAT_Code/c
sudo make clean
sudo make
sudo ./main
