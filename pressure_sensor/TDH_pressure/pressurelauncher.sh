#!/bin/bash

# Mount the SD card for data storage
mkdir /media/wispr_sd
sudo mount -t exfat /dev/mmcblk1p1 /media/wispr_sd

# Launch script for TDH pressure sensor
cd /home/pi/wispr_pi/pressure_sensor/TDH_pressure/
python TDH_pressure.py &
