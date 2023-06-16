import os
import subprocess
from glob import glob


# Set to True to use AWS bucket
AWS = False

# For VPN connection
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
        raise Exception("Could not make server connection")


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


def publish_data(schema, ext):
    data_dir = os.path.join('/dev','sda','wispr_data',schema,'') # !!!
    data_cache_dir = os.path.join('/dev','sda','wispr_data',schema+'.backup','')

    #if not os.path.exists(data_cache_dir):
    #    os.makedirs(data_cache_dir)

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


if __name__ == "__main__":
    # #### Hydrophone ####
    # schema = os.path.join('spar_drifter', 'hydrophone')
    # ext = '.wav'
    # publish_data(schema, ext)

    # #### GPS ####
    # schema = os.path.join('spar_drifter', 'gps')
    # ext = '.txt'
    # publish_data(schema, ext)

    #### Pressure ####
    schema = os.path.join('spar_drifter', 'pressure')
    ext = '.csv'
    publish_data(schema, ext)
