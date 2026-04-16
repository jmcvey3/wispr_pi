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

- Raspberry Pi running Raspberry Pi OS (tested on RPi 3)
- Blue Robotics MS5837-30BA pressure/temperature sensor connected via I²C
- Python 3 with `smbus2`
- exFAT filesystem support (for WISPR SD card)

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/jmcvey3/wispr_pi.git /home/pi/wispr_pi
cd /home/pi/wispr_pi
git submodule update --init --remote
```

### 2. Enable I²C on the Raspberry Pi

```bash
sudo raspi-config
# Navigate to: Interfacing Options → I2C → Enable
```

Install the required Python SMBus library:

```bash
sudo apt-get install python-smbus2
```

### 3. Install the MS5837 pressure sensor driver

```bash
cd /home/pi/wispr_pi/pressure_sensor/blue_robotics_ms5837
sudo pip install -e .
```

### 4. Install exFAT support (required for WISPR SD card)

```bash
sudo apt-get update
sudo apt-get install exfat-fuse exfat-utils
```

### 5. Configure the Raspberry Pi boot settings

Edit `/boot/config.txt` (`sudo nano /boot/config.txt`) and add the following lines. See [config_files/boot_config.txt](config_files/boot_config.txt) for a reference backup:

```ini
# Enable 2nd SD card using the custom overlay (disables WiFi)
dtparam=sdio_overclock=25
dtoverlay=sdio,poll_once=off

# Enable UART communication for WISPR
enable_uart=1
```

### 6. Restore the crontab

Install the backup crontab to start pressure logging on boot and schedule data transfers every 5 minutes:

```bash
sudo crontab /home/pi/wispr_pi/config_files/crontab.bak
```

The configured cron jobs are:

| Schedule | Command |
|----------|---------|
| On reboot | Creates directory for and mounts available WISPR SD card |
| On reboot | Starts `TDH_pressure.py` via `pressurelauncher.sh` |

### 7. Reboot and verify

```bash
sudo reboot
```

After reboot, confirm logging is active:

```bash
ls /media/wispr_sd/pressure_sensor/logs/
```

A log file named `pressure_sensor.<date>.log` should be present.

## Pressure Sensor Data

[`TDH_pressure/TDH_pressure.py`](pressure_sensor/TDH_pressure/TDH_pressure.py) samples the MS5837 sensor at **4 Hz** in 600-second bursts. Each burst writes a CSV file to `pressure_sensor/data/` with the columns:

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
