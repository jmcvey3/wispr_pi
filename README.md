# wispr_pi

Raspberry Pi interfacing scripts for the [WISPR](wispr2_sw/README.md) (Wideband Intelligent Signal Processing and Recording) acoustic recorder. This repository provides:

- **Pressure logging** via a Blue Robotics MS5837-30BA sensor, recorded automatically on boot
- **WISPR firmware** (as a submodule) — Atmel Studio 7 C firmware for the WISPR V2.1 board targeting drifting hydrophone
buoy deployments.

## Repository Structure

```
wispr_pi/
├── clock/
│   ├── set_clock.sh            # Reads WTM epoch from WISPR serial and sets system clock
│   └── wispr-set-clock.service # systemd service to run set_clock.sh on boot
├── config_files/           # Raspberry Pi boot and crontab configuration backups
├── pressure_sensor/
│   ├── ms5837.py           # Blue Robotics MS5837 Python driver
│   ├── mountlauncher.sh    # Waits for WISPR SDIO SD card to enumerate, then mounts it permanently
│   ├── pressurelauncher.sh # Bash script that launches tdh_pressure.py
│   └── tdh_pressure.py     # Burst pressure logging script
└── wispr2_sw/              # WISPR V2 firmware source (git submodule, OSU branch)
```

## Prerequisites

- Raspberry Pi 4 (Rev 1.2) running Raspberry Pi OS (64-bit)
- Blue Robotics MS5837-30BA pressure/temperature sensor connected via I²C (GPIO2/3)
- WISPR V2 board with SDIO secondary SD card wired to GPIO22–27
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

### 3. Clone the Repository
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

### 6. Install exFAT Support (required for WISPR SD card)

```bash
sudo apt-get install autoconf libtool pkg-config
sudo apt-get install exfatprogs
```

### 7. Configure the Raspberry Pi Boot Settings

Edit `/boot/firmware/config.txt` (`sudo nano /boot/firmware/config.txt`) and add the following lines. See [config_files/boot_config.txt](config_files/boot_config.txt) for a reference backup:

```ini
# I2C slowed to 10 kHz (default 100 kHz) for two reasons:
#   1. Reduces harmonic energy radiated by SCL onto nearby wires (WISPR noise).
#   2. Provides settling margin for the ~3 m cable run to the MS5837 sensor.
#      Cable capacitance (~300 pF) + pull-up resistance forms an RC filter;
#      10 kHz gives ~50 µs per half-cycle, well above the ~1 µs RC time constant.
# Note: 4 kHz caused intermittent failures, likely due to the BCM2711 I2C
# hardware timeout (64 clock cycles = 16 ms at 4 kHz) firing during init.
dtparam=i2c_arm=on
dtparam=i2c_arm_baudrate=10000

# Disable audio — BCM2835 audio clocks GPIO12 (PWM0) which is wired to WISPR
# and injects switching noise into acoustic recordings.
dtparam=audio=off

# Disable camera/display auto-detect — no peripherals attached, and probing
# I2C on every boot causes transients.
camera_auto_detect=0
display_auto_detect=0

# Use headless GPU overlay instead of full vc4-kms-v3d to reduce GPU activity.
dtoverlay=vc4-fkms-v3d

# Disable CPU boost — fixed frequency reduces supply current variation
# that can couple into WISPR's analog front end.
# arm_boost=1

# Drive unused GPIO pins wired to WISPR to a defined low state.
# Floating inputs act as antennas and inject noise into WISPR's signal chain.
# 6: unknown, 8-11: SPI0 (disabled), 12: PWM0 (audio off)
gpio=6,8,9,10,11,12=op,dl

# Power down the WiFi/BT chip (BCM43455) entirely.
dtoverlay=disable-wifi
# Free PL011 UART for GPIO14/15 (serial0 -> /dev/ttyAMA0).
dtoverlay=disable-bt

# Enable UART communication for WISPR
enable_uart=1

# Expose WISPR's secondary SD card via SDIO (GPIO22=CLK, GPIO23=CMD, GPIO24-27=DAT0-3).
# poll_once=off polls continuously so the card is detected even if WISPR's
# sd_card_enable() fires late (up to 90s post-boot after GPS PPS sync).
# sdio_overclock=10 slows the SDIO clock to 10 MHz for signal integrity.
dtoverlay=sdio,poll_once=off
dtparam=sdio_overclock=10
```

### 8. Restore the Crontab

Install the backup crontab to mount the SD card and start pressure logging after boot:

```bash
sudo crontab /home/pi/wispr_pi/config_files/crontab.bak
```

The configured cron jobs are:

| Schedule | Command |
|----------|----------|
| On reboot | Runs `mountlauncher.sh`, which waits up to 10 minutes for WISPR's SDIO SD card to enumerate (WISPR calls `sd_card_enable()` after GPS PPS sync, up to ~90s post-boot), mounts it permanently at `/media/wispr_sd`, then starts `tdh_pressure.py` via `pressurelauncher.sh` |

Mount attempts and failures are logged to `/media/wispr_sd/pressure_sensor/logs/mountlauncher.log`.

### 9. Enable the clock sync service

Next, we need to set up the RPi to look for clock messages from the WISPR to update it's clock.
The WISPR sends one message shortly after the RPi boots (45 s, to be exact) and then repeats every 5 minutes.

The following installs a systemd service that listens on the serial port for `WTM,<epoch>` messages from the WISPR and sets the RPi system clock accordingly. 

```bash
sudo cp /home/pi/wispr_pi/clock/wispr-set-clock.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now wispr-set-clock
```

Verify it is running:

```bash
systemctl status wispr-set-clock
```

The service will start automatically on every subsequent boot. Clock sync events are logged to the system journal and can be viewed with:

```bash
journalctl -t wispr-set-clock
```

### 10. Reboot and Verify

```bash
sudo reboot now
```

After reboot, you'll no longer be able to ssh in over Wifi.
Connect an ethernet cable to the rPi and then to your computer, remembering to disable your computer's wifi.
Log in using `ssh pi@raspberrypi.local`.

Confirm the WISPR SD card is mounted and pressure logging is active:

```bash
ls /media/wispr_sd/pressure_sensor/data/
ls /media/wispr_sd/pressure_sensor/logs/
```

Both data files (`pressure_sensor.<date>.<time>.csv`) and log files (`pressure_sensor.<date>.log`) are written to the WISPR SD card.

## Reading WISPR Com & Console Output
Because the WISPR com and console output are directed through UART1, and UART1 is now connected
to the RPi, one must remote into the RPi and stop the clock script to see the WISPR output.

First, ssh into the RPi:
```bash
ssh pi@raspberrypi.local
```
Then stop the clock update script and open the serial port:
```bash
sudo systemctl stop wispr-set-clock
stty -F /dev/serial0 9600
cat /dev/serial0
```

Use `ctrl+c` to quit. Then restart the clock update script:
```bash
sudo systemctl start wispr-set-clock
```

Note: any `WTM` clock sync messages sent by the WISPR while the service is stopped will be
printed to the terminal but not applied. The next sync will occur within 5 minutes once the
service is restarted.

## Pressure Sensor Data

[`tdh_pressure.py`](pressure_sensor/tdh_pressure.py) samples the MS5837 sensor at **4 Hz** in 60-second bursts. Each burst writes a CSV file to `pressure_sensor/data/` with the columns

```
timestamp (UTC), pressure (dbar), temperature (°C)
```

## PNNL/OSU Drifter Buoy Electronics Startup Procedure
1. Power on the buoy using the dummy plug on the top of the spar buoy. If power from the battery is flowing, the red LED will turn on.
2. The WISPR powers on and starts searching for GPS signal. Once a PPS signal is locked, it powers on the Raspberry Pi and begins hydrophone data collection at 50 kHz and writing a new dat file every 30 seconds.
3. Once the RPi powers on, the green LED in the top plate of the spar buoy lights up. The RPi begins polling for the WISPR's secondary SD card, and it will make attempts to do so for 10 minutes.
4. Once the card is mounting, it begins recording pressure sensor readings and stores those files on the SD card.
5. After powering on the RPi and running data collection, the WISPR sends a synchronization message to the RPi's clock and updates the GPS location every 15 seconds. It periodically sends a clock update message to the RPi then every 5 minutes.
6. To power down the buoy, remove the dummy plug. 
7. Passive acoustic and pressure data must be recovered from the WISPR SD cards. Wipe the cards before each deployment.

## WISPR Firmware

The [`wispr2_sw/`](wispr2_sw/) submodule contains Atmel Studio 7 project files and C source code for the WISPR V2 board (SAM microcontroller, LTC2512 ADC). Multiple deployment configurations are provided:

| Project | Description |
|---------|-------------|
| `wispr_drifter` | PNNL acoustic drifter — continuous DAQ, GPS PPS sync |
| `wispr_crab` | PMEL CRAB buoy recorder |
| `wispr_perimeter` | Perimeter mooring recorder |
| `wispr_hawaii_glider` | Hawaii glider deployment |

See [wispr2_sw/README.md](wispr2_sw/README.md) for firmware build instructions.
