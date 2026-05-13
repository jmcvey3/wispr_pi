import os
import time
import logging
from datetime import datetime, timezone

import ms5837

# Define loop constants
burst_time = 0
burst_seconds = 60
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
logging.info("Starting tdh_pressure.py")

# initialize pressure sensor
sensor = ms5837.MS5837_30BA()  # Default I2C bus is 1 (Raspberry Pi 3)
# sensor.setFluidDensity(ms5837.DENSITY_SALTWATER)

# Initialize the sensor and report any errors
try:
    if not sensor.init():
        logging.info("Sensor could not be initialized")
        exit(1)
except Exception as e:
    logging.error("Error initializing pressure sensor")
    logging.error(e)
    exit(1)

# Perform a read to populate the sensor's internal state and report any errors
try:
    if not sensor.read():
        logging.error("Sensor read failed!")
        exit(1)
except Exception as e:
    logging.error("Error reading pressure sensor data")
    logging.error(e)
    exit(1)

# Log pressure and temperature readings
logging.info("Pressure sensor initialized successfully")
isample = 0
while True:
    now = datetime.now(timezone.utc)
    # Start a new burst of pressure data collection at the specified time and interval
    if now.minute == burst_time or now.minute % burst_interval == 0 and now.second == 0:
        # Create a new data file for this sample burst of pressure data collection
        fname = os.path.join(
            data_path,
            "pressure_sensor." + datetime.strftime(now, "%Y%m%d.%H%M%S") + ".csv",
        )
        logging.info("Open file for writing: %s" % fname)

        isample = 0
        t_end = time.time() + burst_seconds

        with open(fname, "w", newline="\n") as f_out:
            f_out.write("timestamp,pressure_dbar,temperature_C\n")

            while (time.time() <= t_end) or (isample < pressure_samples):
                timestamp = datetime.now(timezone.utc)
                try:
                    sensor.read()
                    P = sensor.pressure(ms5837.UNITS_bar) * 10
                    T = sensor.temperature(ms5837.UNITS_Centigrade)
                except Exception as e:
                    P = -9999
                    T = -9999
                    logging.error("Error reading pressure sensor")
                    logging.error(e)

                timestr = "{:%Y-%m-%d %H:%M:%S.%f}".format(timestamp)
                f_out.write("%s,%f,%f\n" % (timestr, P, T))
                f_out.flush()

                isample = isample + 1

                # Hard-coded sleep to control recording rate. Not ideal but works
                time.sleep(1 / pressureFreq)

        logging.info("Write complete")
