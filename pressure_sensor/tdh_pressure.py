import os
import time
import logging
from datetime import datetime, timedelta, timezone
import ms5837

# Define loop constants
sensor_read_time = (
    0.044  # s, time it takes to read the sensor (experimentally determined)
)
burst_seconds = 60
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
logging.info("-------------------------------")
logging.info("Starting tdh_pressure.py")

# Initialize pressure sensor
sensor = ms5837.MS5837_30BA()  # Default I2C bus is 1

# Initialize the sensor and report any errors
try:
    if not sensor.init():
        logging.error("Sensor could not be initialized")
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
    # Create a new data file for this sample burst of pressure data collection
    now = datetime.now(timezone.utc)
    fname = os.path.join(
        data_path,
        "pressure_sensor." + datetime.strftime(now, "%Y%m%d.%H%M%S") + ".csv",
    )
    logging.info("Open file for writing: %s" % fname)

    isample = 0
    t_end = now + timedelta(seconds=burst_seconds)

    with open(fname, "w", newline="\n") as f_out:
        f_out.write("timestamp,pressure_dbar,temperature_C\n")

        while (datetime.now(timezone.utc) <= t_end) or (isample <= pressure_samples):
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

            # Hard-code sleep to control recording rate, depends on RPi load and sensor read time.
            # With testing, if pressureFreq = 4 Hz, then the actual rate is about 3.40 Hz,
            # which means the sensor read time is about 0.044 seconds
            time.sleep(1 / pressureFreq - sensor_read_time)

    logging.info("Write complete")
