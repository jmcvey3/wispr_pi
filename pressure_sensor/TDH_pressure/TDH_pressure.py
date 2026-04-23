import os
import time
import logging
from datetime import datetime, timezone

import ms5837


# Define loop constants
burst_time = 0
burst_seconds = 600
burst_interval = 1
pressureFreq = 4
pressure_samples = pressureFreq * burst_seconds

sd_mount = os.path.join("/", "media", "wispr_sd")
log_path = os.path.join(sd_mount, "pressure_sensor", "logs")
data_path = os.path.join(sd_mount, "pressure_sensor", "data")

if not os.path.exists(log_path):
    os.makedirs(log_path)
if not os.path.exists(data_path):
    os.makedirs(data_path)

# Set up logging file
now = datetime.now(timezone.utc)
logger = logging.getLogger("system_logger")
LOG_FILE = os.path.join(
    log_path,
    "pressure_sensor." + datetime.strftime(now, "%Y%m%d") + ".log",
)
logging.basicConfig(
    filename=LOG_FILE,
    format="%(asctime)s, %(filename)s - [%(levelname)s] - %(message)s",
    level=logging.DEBUG,
)
logging.info("-------------------TDH_pressuresensor.py-----------------")

# initialize pressure sensor
sensor = ms5837.MS5837_30BA()  # Default I2C bus is 1 (Raspberry Pi 3)
sensor.setFluidDensity(ms5837.DENSITY_SALTWATER)

# We must initialize the sensor before reading it
if not sensor.init():
    logging.info("Sensor could not be initialized")
    exit(1)

# We have to read values from sensor to update pressure and temperature
if not sensor.read():
    logging.error("Sensor read failed!")
    exit(1)

logging.info("Pressure sensor initialized successfully")
isample = 0
while True:
    now = datetime.now(timezone.utc)
    if now.minute == burst_time or now.minute % burst_interval == 0 and now.second == 0:

        fname = os.path.join(
            data_path,
            "pressure_sensor." + datetime.strftime(now, "%Y%m%d") + ".csv",
        )
        logging.info("Filename: %s" % fname)

        with open(fname, "w", newline="\n") as f_out:
            logging.info("Open file for writing: %s" % fname)
            f_out.write("timestamp,pressure_dbar,temperature_C\n")
            t_end = time.time() + burst_seconds
            isample = 0
            while time.time() <= t_end or isample < pressure_samples:
                try:
                    P = sensor.pressure(ms5837.UNITS_bar) * 10
                    T = sensor.temperature(ms5837.UNITS_Centigrade)
                except Exception as e:
                    P = -9999
                    T = -9999
                    logging.error("Error reading pressure sensor data")
                    logging.error(e)

                timestamp = "{:%Y-%m-%d %H:%M:%S.%f}".format(now)
                f_out.write("%s,%f,%f\n" % (timestamp, P, T))
                f_out.flush()

                isample = isample + 1
                if time.time() >= t_end and 0 < pressure_samples - isample <= 40:
                    continue
                elif time.time() > t_end and pressure_samples - isample > 40:
                    break

                logging.info("Pressure Sample %s completed" % isample)

                # Hard-coded sleep to control recording rate. Not ideal but works
                time.sleep(0.065)

        time.sleep(0.50)
