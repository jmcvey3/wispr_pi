import os
import subprocess
import logging
from glob import glob
from datetime import datetime

""" 
This file is set up to transfer data from the WISPR's SD card over the cloud to 
a server. Transferred data is moved to a ".backup" folder after it is sent.

Hydrophone and GPS data is being recorded by the wispr and saved on the SD card.
Pressure sensor data, collected by the Raspberry Pi, is recorded on the Pi's 
storage drive and is transferred to the wispr's SD card via this script.

Two functions are provided to transfer data over AWS or an ssh connection.
For the former, AWS S3 bucket keys should be set on the rPi. For the latter, a 
VPN connection needs to be set up on the rPi.
"""

# Set to True to use AWS bucket, otherwise defaults to using ssh over VPN
AWS = False

# For ssh'ing over a VPN connection
USER = 'OSU'
SERVER = '192.168.0.2'

# For AWS bucket
BUCKET = 'hydrophone_drifters'

###############################################################################
def save_to_aws(filepath, filename, shema):
    import boto3
    # Use raspberry pi serial number to differentiate between drifters
    sn = get_rpi_serial()

    # Need to run 'aws config' to allow connection to AWS
    s3_resource = boto3.resource('s3')
    bucket_dir = os.path.join(schema, f'SN{sn}')
    s3_key = bucket_dir + filename

    print("saving to s3: " + filepath)
    s3_resource.Bucket(BUCKET).upload_file(Filename=filepath, Key=s3_key)


def secure_copy(filepath, filename, schema):
    # Use raspberry pi serial number to differentiate between drifters
    sn = get_rpi_serial()

    # "scp" to destination
    folder_dir = os.path.join(schema, f'SN{sn}')
    scp_path = folder_dir + filename
    try:
        subprocess.run(["scp", filepath, f"{USER}@{SERVER}:{scp_path}"])
    except:
        logging.error(f"Could not make server connection: {USER}@{SERVER}:{scp_path}")


def get_rpi_serial():
    # Extract serial from cpuinfo file
    cpuserial = "0000000000000000"
    try:
        f = open('/proc/cpuinfo','r')
        for line in f:
            if line[0:6]=='Serial':
                cpuserial = line[10:26]
        f.close()
    except:
      cpuserial = "ERROR000000000"
     
    return cpuserial


def init_logger():
    ## Assert connection to /media/wispr_sd and log
    logger = logging.getLogger(__name__)
    log_path = os.path.join('/','home','pi','wispr_pi','wispr_telemetry','logs','')
    if not os.path.exists(log_path):
        os.makedirs(log_path)
    logging.basicConfig(filename=log_path+'telemetry_'+datetime.strftime(datetime.now(),'%d%b%Y')+'.log',
                        level=logging.NOTSET,
                        format='%(asctime)s, %(name)s - %(levelname)s - %(message)s')
    
    logging.info('-------------------transfer_data.py-----------------')

    if os.path.exists('/media/wispr_sd'):
        logging.debug('SD card directory accessible')
    else:
        logging.error('SD card directory not found')
        

def publish_data(data_dir, schema, ext):
    logging.info(f"Transferring {schema}...")

    data_cache_dir = os.path.join('/','media','wispr_sd',schema+'.backup','')

    if not os.path.exists(data_cache_dir):
       os.makedirs(data_cache_dir)

    # copy the files to S3, move them to the backup location
    filepaths = glob(os.path.join(data_dir,'*'+ext))

    for fpath in filepaths:
        filename = os.path.basename(fpath)

        # Check for and skip sending empty files
        fsize = os.stat(fpath).st_size
        if not fsize:
            pass
        else:
            # Filepath contains filename
            if AWS:
                save_to_aws(fpath, filename, schema)
            else:
                secure_copy(fpath, filename, schema)
        try:
            os.rename(fpath, os.path.join(data_cache_dir,filename))
        except:
            pass
    
    logging.info("Completed transfer")


if __name__ == "__main__":
    init_logger()

    #### Hydrophone ####
    # TODO Create data product to send to server
    data_dir = os.path.join('/','media','wispr_sd','hydrophone')
    schema = 'hydrophone'
    ext = '.wav'
    publish_data(data_dir, schema, ext)

    #### GPS ####
    # TODO Convert NMEA strings to csv
    data_dir = os.path.join('/','media','wispr_sd','gps')
    schema = 'gps'
    ext = '.txt'
    publish_data(data_dir, schema, ext)

    #### Pressure ####
    data_dir = os.path.join('/','home','pi','wispr_pi','pressure_sensor','data')
    schema = 'pressure'
    ext = '.csv'
    publish_data(data_dir, schema, ext)
