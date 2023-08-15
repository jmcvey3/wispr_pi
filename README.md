# wispr_pi
Raspberry Pi to WISPR interfacing scripts

## Setup
1. Git clone this repo to the /home/pi directory on the WISPR's Raspberry Pi
```
git clone https://github.com/jmcvey3/wispr_pi.git
cd wispr_pi
git submodule update --init --remote
```
2. Navigate to 'blue_robotics_ms5837' (pressure sensor) and install:
```bash
cd /home/pi/wispr_pi/pressure_sensor/blue_robotics_mw5837
sudo pip install -e .
```

3. Use the backup crontab ('crontab.bak') and restore the root crontab 
```bash
sudo crontab /home/pi/wispr_pi/config_files/crontab.bak
```
   The crontab is set to start recording pressure sensor data on boot, as well as to send data to backup
   every 5 minutes.
 
4. If using AWS S3 to store data in the cloud, please `pip install boto3` and follow the instructions in "How to Install AWS-CLI on rPi.pdf" to set up S3 access keys.

5. Reboot and ensure a pressure sensor log is recorded in /home/pi/wispr_pi/PressureSensor/logs

The following steps are related to those listed in in wispr_rpi.docx

6. First install support for exFAT on your RPi using the following commands:
```bash
sudo apt-get update
sudo apt-get install exfat-fuse exfat-utils 
```

7. Navigate to the boot configuration file (`sudo nano /boot/config.txt`) and add the following lines (See config_files/boot_config.txt for a backup file):
```bash
# Enable 2nd SD card using the custom overlay (disables wifi)
dtparam=sdio_overclock=25
dtoverlay=sdio,poll_once=off

# Enable UART communication for the wispr
enable_uart=1
```
