# wispr_pi

Raspberry Pi interfacing scripts for the [WISPR](wispr2_sw/README.md) (Wideband Intelligent Signal Processing and Recording) acoustic recorder. This repository provides:

- **Pressure/depth logging** via a Blue Robotics MS5837-30BA sensor, recorded automatically on boot
- **WISPR firmware** (as a submodule) — Atmel Studio 7 C firmware for the WISPR V2 board targeting hydrophone deployments such as drifters, CRAB buoys, perimeter moorings, and Hawaii gliders

## Repository Structure

```
wispr_pi/
├── config_files/          # Raspberry Pi boot and crontab configuration backups
├── pressure_sensor/
│   ├── blue_robotics_ms5837/  # MS5837 Python driver (git submodule)
│   ├── data/              # CSV pressure/temperature/depth data output
│   ├── logs/              # Pressure logger log files
│   └── TDH_pressure/      # Burst pressure logging script and launcher
└── wispr2_sw/             # WISPR V2 firmware source (git submodule, OSU branch)
```

## Prerequisites

- Raspberry Pi 4 (Rev 1.2) running Raspberry Pi OS (64-bit)
- Blue Robotics MS5837-30BA pressure/temperature sensor connected via I²C
- Python 3 with `smbus2` (`python3-smbus2`)
- exFAT filesystem support (for WISPR SD card)

## Setup

### 0. Install latest Raspberry Pi OS
Open Raspberry Pi Imager software and flash a fresh SD card. For Raspberry Pi 4B, use lastest 64 bit firmware
1. Set hostname as "raspberrypi"
2. Set the clock to UTC.
3. Enable wifi connection and SSH so you can remote into the pi
4. This README assumes the username is "pi". Do not forget your password.

## Remote into Raspberry Pi
1. Power on rPi
2. Plug rPi into computer using ethernet cable and turn off your computer's wifi
3. Log in via `ssh pi@raspberrypi.local`. It may take a minute for the rPi to wake
4. Once logged in, run `ip route list` to get your rPi's assigned DHCP address
5. If one isn't assigned, unplug the ethernet cable, wait a minute to allow the router to assign one, then plug back in
6. Once you see a router-assigned IP (wlan0), unplug the ethernet cable
7. Turn wifi back on your computer and ssh into the rPi using the IP address (`ssh pi@<xxx.xxx.xxx.xxx>`)

### 1. Clone the repository
Clone or download the repository to your laptop, then copy to the Raspberry Pi through wifi:
```bash
git clone https://github.com/jmcvey3/wispr_pi.git .
scp -r wispr_pi pi@raspberrypi.local:/home/pi/
```

### 2. Enable I²C on the Raspberry Pi (required for pressure sensor)

```bash
sudo raspi-config
# Navigate to: Interfacing Options → I2C → Enable
```

### 3. Disable Serial and enable SPI (required for WISPR connection)

```bash
sudo raspi-config
# Navigate to: Interfacing Options → Serial → Disable -> Enable
# Navigate to: Interfacing Options → SPI -> Enable
```
Then navigate to finish and hit enter. Do not reboot yet.

Next, install the required Python SMBus library:

```bash
sudo apt-get update
sudo apt-get install python3-smbus2
```

### 3. Install exFAT support (required for WISPR SD card)

```bash
sudo apt-get install autoconf libtool pkg-config
sudo apt-get install exfatprogs
```

### 4. Configure the Raspberry Pi boot settings

Edit `/boot/firmware/config.txt` (`sudo nano /boot/firmware/config.txt`) and add the following lines. See [config_files/boot_config.txt](config_files/boot_config.txt) for a reference backup:

```ini
# Enable 2nd SD card using the custom overlay (disables WiFi)
# use polling timer to avoid known rPi4 issue
dtoverlay=sdio,poll_once=off,polling_ms=1000

# Enable UART communication for WISPR
# On RPi 4, Bluetooth occupies the PL011 UART by default, pushing serial0 onto
# the mini-UART (ttyS0) whose baud rate is tied to the VPU clock and is unreliable.
# disable-bt frees PL011 for GPIO14/15 (serial0 -> /dev/ttyAMA0).
dtoverlay=disable-bt
enable_uart=1
```

### 5. Restore the crontab

Install the backup crontab to start pressure logging on boot and schedule data transfers every 5 minutes:

```bash
sudo crontab /home/pi/wispr_pi/config_files/crontab.bak
```

The configured cron jobs are:

| Schedule | Command |
|----------|---------|
| On reboot | Waits 60 s, then creates `/media/wispr_sd` and mounts the WISPR SD card (`/dev/mmcblk1p1`) |
| On reboot | Waits 80 s, then starts `tdh_pressure.py` via `pressurelauncher.sh` |

### 6. Reboot and verify

```bash
sudo reboot
```

After reboot, you'll no longer be able to ssh in over Wifi.
Connect an ethernet cable to the rPi and then to your laptop.
Log in using `ssh pi@raspberrypi.local`. You may need to disable your wifi.

Confirm the WISPR SD card is mounted and pressure logging is active:

```bash
ls /media/wispr_sd/
ls /home/pi/wispr_sd/pressure_sensor/logs/
```

A log file named `pressure_sensor.<date>.log` should be present.

## Pressure Sensor Data

[`tdh_pressure.py`](pressure_sensor/tdh_pressure.py) samples the MS5837 sensor at **4 Hz** in 600-second bursts. Each burst writes a CSV file to `pressure_sensor/data/` with the columns:

```
UTC timestamp, pressure (psi), temperature (°F), depth (m)
```

Example output file: [`pressure_sensor/data/pressure_sensor.20230508.csv`](pressure_sensor/data/pressure_sensor.20230508.csv)

## WISPR Firmware

The [`wispr2_sw/`](wispr2_sw/) submodule contains Atmel Studio 7 project files and C source for the WISPR V2 board (SAM microcontroller, LTC2512 ADC). Multiple deployment configurations are provided:

| Project | Description |
|---------|-------------|
| `wispr_drifter` | PNNL acoustic drifter — continuous DAQ, GPS PPS sync |
| `wispr_crab` | PMEL CRAB buoy recorder |
| `wispr_perimeter` | Perimeter mooring recorder |
| `wispr_hawaii_glider` | Hawaii glider deployment |

See [wispr2_sw/README.md](wispr2_sw/README.md) for firmware build instructions.
