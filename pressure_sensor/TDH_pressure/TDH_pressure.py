import os
import time
import logging
from datetime import datetime

import ms5837


# Define loop constants
burst_time = 0
burst_seconds = 600
burst_interval = 1
pressureFreq = 4
pressure_samples = pressureFreq * burst_seconds

log_path = os.path.join('/','home','pi','wispr_pi','pressure_sensor','logs')
data_path = os.path.join('/','home','pi','wispr_pi','pressure_sensor','data')

if not os.path.exists(log_path):
      os.makedirs(log_path)
if not os.path.exists(data_path):
      os.makedirs(data_path)

# Set up logging file
logger = logging.getLogger('system_logger')
LOG_FILE = os.path.join(log_path,'pressureSensorLog_' + datetime.strftime(datetime.now(), '%d%b%Y') + '.log')
logging.basicConfig(filename=LOG_FILE, 
                    format='%(asctime)s, %(filename)s - [%(levelname)s] - %(message)s', 
                    level=logging.DEBUG)

#initialize pressure sensor
sensor = ms5837.MS5837_30BA() # Default I2C bus is 1 (Raspberry Pi 3)
sensor.setFluidDensity(ms5837.DENSITY_SALTWATER)

# We must initialize the sensor before reading it
if not sensor.init():
        logging.info("Sensor could not be initialized")
        exit(1)

# We have to read values from sensor to update pressure and temperature
if not sensor.read():
    logging.info("Sensor read failed!")
    exit(1)

pressure = []
isample = 0
tsart = time.time()

logging.info('-------------------TDH_pressuresensor.py-----------------')
while True:
      now = datetime.utcnow()
      if now.minute == burst_time or now.minute % burst_interval == 0 and now.second == 0:
            
            logging.info('starting burst')
            fname = os.path.join(data_path, 'pressureSensorData_' + datetime.strftime(datetime.now(), '%d%b%Y') + '.csv')
            logging.info('file name: %s' %fname)

            with open(fname, 'w',newline = '\n') as pressure_out:
                  logging.info('open file for writing: %s' %fname)
                  t_end = time.time() + burst_seconds
                  isample =0
                  while time.time() <= t_end or isample < pressure_samples:
                        try:
                              P = sensor.pressure(ms5837.UNITS_psi)
                              T = sensor.temperature(ms5837.UNITS_Farenheit)
                              D = sensor.depth()
                        except Exception as e:
                              logging.info(e)
                              logging.info('error reading pressure sensor data')

                        timestamp = '{:%Y-%m-%d %H:%M:%S.%f}'.format(datetime.utcnow())
                        pressure_out.write('%s,%f,%f,%f\n' %(timestamp,P,T,D))
                        pressure_out.flush()

                        isample = isample + 1
                        if time.time() >= t_end and 0 < pressure_samples-isample <= 40:
                            continue
                        elif time.time() > t_end and pressure_samples-isample > 40:
                            break
                        
                        #hard coded sleep to control recording rate. NOT ideal but works for now    
                        time.sleep(0.065)

                        logging.info('end burst')
                        logging.info('Pressure Sample %s' %isample)

            time.sleep(.50)


