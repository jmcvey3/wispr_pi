# wispr_pi

Raspberry Pi interfacing scripts for the [WISPR](wispr2_sw/README.md) (Wideband Intelligent Signal Processing and Recording) acoustic recorder. This repository provides:

- **Pressure logging** via a Blue Robotics MS5837-30BA sensor, recorded automatically on boot
- **WISPR firmware** (as a submodule) — Atmel Studio 7 C firmware for the WISPR V2 board targeting hydrophone deployments such as drifters, CRAB buoys, perimeter moorings, and Hawaii gliders

## Repository Structure

```
wispr_pi/
├── config_files/           # Raspberry Pi boot and crontab configuration backups
├── pressure_sensor/
│   ├── data/               # CSV pressure/temperature/depth data output
│   ├── logs/               # Pressure logger log files
│   ├── ms5837.py           # Blue Robotics MS5837 Python driver
│   ├── mountlauncher.sh    # Retry-loop script to mount WISPR SD card on boot
│   ├── pressurelauncher.sh # Bash script that runs logging script
│   └── tdh_pressure.py     # Burst pressure logging script
└── wispr2_sw/              # WISPR V2 firmware source (git submodule, OSU branch)
```

## Prerequisites

- Raspberry Pi 4 (Rev 1.2) running Raspberry Pi OS (64-bit)
- Blue Robotics MS5837-30BA pressure/temperature sensor connected via I²C
- Python 3 with `smbus2` (`python3-smbus2`)
- exFAT filesystem support (for WISPR SD card)

## Setup

### 1. Install latest Raspberry Pi OS
Open Raspberry Pi Imager software and flash a fresh SD card. For Raspberry Pi 4B, use the lastest 64 bit firmware:
1. Set hostname as "raspberrypi".
2. Set the clock to UTC.
3. Enable wifi connection and SSH so you can remote into the pi.
4. This README assumes the username is "pi". Do not forget your password.

### 2. Remote into Raspberry Pi
1. Power on rPi
2. Plug rPi into computer using an ethernet cable and turn off your computer's wifi.
3. Log in via `ssh pi@raspberrypi.local`. It may take a minute for the rPi to wake.
4. Once logged in, run `ip route list` to get your rPi's assigned DHCP address.
5. If one isn't assigned, unplug the ethernet cable, wait a minute to allow the router to assign one, then plug back in.
6. Once you see a router-assigned IP (under "wlan0"), unplug the ethernet cable.
7. Turn wifi back on your computer and ssh into the rPi using the IP address (`ssh pi@<xxx.xxx.xxx.xxx>`).

### 3. Clone the repository
Clone or download the repository to your laptop, then copy to the Raspberry Pi:
```bash
git clone https://github.com/jmcvey3/wispr_pi.git .
scp -r wispr_pi pi@raspberrypi.local:/home/pi/
```

### 4. Enable I²C on the Raspberry Pi (required for pressure sensor)

```bash
sudo raspi-config
# Navigate to: Interfacing Options → I2C → Enable
```

### 5. Disable Serial (required for WISPR connection)

```bash
sudo raspi-config
# Navigate to: Interfacing Options → Serial → Disable → Enable
# Then navigate to Finish and hit Enter. Do not reboot yet.
```

Next, install the required Python SMBus library if it isn't already natively installed:

```bash
sudo apt-get update
sudo apt-get install python3-smbus2
```

### 6. Install exFAT support (required for WISPR SD card)

```bash
sudo apt-get install autoconf libtool pkg-config
sudo apt-get install exfatprogs
```

### 7. Configure the Raspberry Pi boot settings

Edit `/boot/firmware/config.txt` (`sudo nano /boot/firmware/config.txt`) and add the following lines. See [config_files/boot_config.txt](config_files/boot_config.txt) for a reference backup:

```ini
## Enable 2nd SD card using the custom overlay (disables WiFi).
# polling_ms avoids the RPi4 kernel poll_once race with WISPR's sd_card_enable().
dtoverlay=sdio,poll_once=off,polling_ms=1000

# Slow down the SDIO clock to not crash the RPi
dtparam=sdio_overclock=10

# NOTE: SPI must remain disabled (dtparam=spi=on must NOT be set).
# GPIO8-11 (SPI0) are wired to WISPR; enabling the RPi SPI controller
# would drive those lines and interfere with WISPR's operation.

# Enable UART communication for WISPR
enable_uart=1

# On RPi 4, Bluetooth occupies the PL011 UART by default, pushing serial0 onto the mini-UART (ttyS0) whose baud rate is tied to the VPU clock and is unreliable. disable-bt frees PL011 for GPIO14/15 (serial0 -> /dev/ttyAMA0).
dtoverlay=disable-bt
```

### 8. Restore the crontab

Install the backup crontab to mount the SD card and start pressure logging after boot:

```bash
sudo crontab /home/pi/wispr_pi/config_files/crontab.bak
```

The configured cron jobs are:

| Schedule | Command |
|----------|---------|
| On reboot | Runs `mountlauncher.sh`, which retries mounting the WISPR SD card every 10 s (up to 20 attempts) until it succeeds, then starts `tdh_pressure.py` via `pressurelauncher.sh` |

Mount attempts and failures are logged to `pressure_sensor/logs/mountlauncher.log`.

### 9. Reboot and verify

```bash
sudo reboot
```

After reboot, you'll no longer be able to ssh in over Wifi.
Connect an ethernet cable to the rPi and then to your computer, remembering to disable your computer's wifi.
Log in using `ssh pi@raspberrypi.local`.

Confirm the WISPR SD card is mounted and pressure logging is active:

```bash
ls /media/wispr_sd/pressure_sensor/data/
ls /media/wispr_sd/pressure_sensor/logs/
```

A log file named `pressure_sensor.<date>.log` should be present in the latter.

## Pressure Sensor Data

[`tdh_pressure.py`](pressure_sensor/tdh_pressure.py) samples the MS5837 sensor at **4 Hz** in 600-second bursts. Each burst writes a CSV file to `pressure_sensor/data/` with the columns

```
timestamp (UTC), pressure (dbar), temperature (°C)
```

Example output file: [`pressure_sensor/data/pressure_sensor.20230508.csv`](pressure_sensor/data/pressure_sensor.20230508.csv)

## WISPR Firmware

The [`wispr2_sw/`](wispr2_sw/) submodule contains Atmel Studio 7 project files and C source code for the WISPR V2 board (SAM microcontroller, LTC2512 ADC). Multiple deployment configurations are provided:

| Project | Description |
|---------|-------------|
| `wispr_drifter` | PNNL acoustic drifter — continuous DAQ, GPS PPS sync |
| `wispr_crab` | PMEL CRAB buoy recorder |
| `wispr_perimeter` | Perimeter mooring recorder |
| `wispr_hawaii_glider` | Hawaii glider deployment |

See [wispr2_sw/README.md](wispr2_sw/README.md) for firmware build instructions.
