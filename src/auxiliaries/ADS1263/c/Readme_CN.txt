/*****************************************************************************
* | File      	:   Readme_CN.txt
* | Author      :   Waveshare team
* | Function    :   Help with use
* | Info        :
*----------------
* |	This version:   V1.0
* | Date        :   2020-12-15
* | Info        :   �������ṩһ�����İ汾��ʹ���ĵ����Ա���Ŀ���ʹ��
******************************************************************************/
����ļ��ǰ�����ʹ�ñ����̡�

1.������Ϣ��
�����̻�����ݮ��4B+�����ģ��ں˰汾
	Linux raspberrypi 5.4.51-v7l+ #1333 SMP Mon Aug 10 16:51:40 BST 2020 armv7l GNU/Linux
������ڹ��̵�main.py�в鿴��ϸ�Ĳ�������

2.�ܽ����ӣ�
�ܽ������������ lib/Config/DEV_Config.c(h) �в鿴������Ҳ������һ�Σ�
SPI:
	AD HAT =>    RPI(BCM)
	VCC    ->    û��ֱ�����ӣ�ʹ�õ�5Vת��3.3V�������豸ʹ�ÿ���ֱ�ӽ�3.3V
	GND    ->    GND
	DIN    ->    10(MOSI)
	DOUT   ->    9(MISO)
	SCLK   ->    11(SCLK)
	CS     ->    22
	DRDY   ->    17
	REST   ->    18
	AVDD   ->    5V��2.5V
	AVSS   ->    GND��-2.5V

3.����ʹ�ã�
����Ӳ��Ĭ��COM�Ѿ����ӵ�GND���������ú���IN0��IN1����ģ���������ʱ���������IN0��IN1��GND����Ŀ���ѹ
���룺
	sudo make clean
	sudo make
	sudo ./main