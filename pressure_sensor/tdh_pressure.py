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

data_path = "/media/wispr_sd/pressure_sensor/data"
log_path = "/media/wispr_sd/pressure_sensor/logs"

os.makedirs(log_path, exist_ok=True)

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

logging.info("Pressure sensor initialized successfully")

while True:
    # Collect one burst into memory.
    now = datetime.now(timezone.utc)
    fname = "pressure_sensor." + datetime.strftime(now, "%Y%m%d.%H%M%S") + ".csv"
    logging.info("Collecting burst: %s" % fname)

    rows = ["timestamp,pressure_dbar,temperature_C\n"]
    isample = 0
    while isample <= pressure_samples:
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
        rows.append("%s,%f,%f\n" % (timestr, P, T))
        isample += 1
        time.sleep(1 / pressureFreq - sensor_read_time)

    logging.info("Burst complete — writing to SD card")
    try:
        with open(os.path.join(data_path, fname), "w", newline="\n") as f_out:
            f_out.writelines(rows)
        logging.info("Write complete: %s" % fname)
    except Exception as e:
        logging.error("Error writing burst file: %s" % e)
