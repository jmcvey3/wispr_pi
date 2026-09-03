import time
from datetime import datetime, timezone
import ms5837

# Define loop constants
sensor_read_time = (
    0.044  # s, time it takes to read the sensor (experimentally determined)
)
burst_seconds = 60
pressureFreq = 4
pressure_samples = pressureFreq * burst_seconds

# Initialize pressure sensor
sensor = ms5837.MS5837_30BA()  # Default I2C bus is 1

# Initialize the sensor and report any errors
try:
    for attempt in range(5):
        try:
            initiated = sensor.init()
        except OSError:
            pass
        if initiated:
            break
        time.sleep(1)
    if not initiated:
        raise ValueError("Sensor could not be initialized")
except Exception as e:
    print(e)
    raise ValueError("Error initializing pressure sensor")
print("Sensor intiated")

# Perform a read to populate the sensor's internal state and report any errors
try:
    for attempt in range(5):
        try:
            read = sensor.read()
        except OSError:
            pass
        if read:
            break
        time.sleep(1)
    if not read:
        raise ValueError("Sensor read failed!")
except Exception as e:
    print(e)
    raise ValueError("Error reading pressure sensor data")
print("Sensor read functional")

# Main loop
while True:
    # Collect one burst into memory.
    now = datetime.now(timezone.utc)
    timestamp = datetime.strftime(now, "%Y%m%d.%H%M%S")

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

        timestr = "{:%Y-%m-%d %H:%M:%S.%f}".format(timestamp)
        rows.append("%s,%f,%f\n" % (timestr, P, T))
        isample += 1
        time.sleep(1 / pressureFreq - sensor_read_time)

        print(f"{timestamp}, pressure={P}, temperature={T}")
