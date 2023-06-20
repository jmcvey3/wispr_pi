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
    sudo crontab /home/pi/wispr_pr/config_files/crontab.bak
```

4. Set up the additional rPi settings as specified in wispr_pi.docx - files are backed up in ./config_files

5. Reboot and ensure a pressure sensor log is recorded in /home/pi/wispr_pi/PressureSensor/logs
