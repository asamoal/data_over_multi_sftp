import sys

import paramiko
import os
import argparse
import itertools
import json
import logging

# Check and create logs directory if not exists
if not os.path.exists('logs'):
    os.makedirs('logs')

# Configure logging
logging.basicConfig(filename='logs/sftp_transfers.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# Creating a separate logger for upload manifest
manifest_logger = logging.getLogger('manifest')
manifest_handler = logging.FileHandler('logs/upload_manifest.log')
manifest_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
manifest_logger.addHandler(manifest_handler)
manifest_logger.setLevel(logging.INFO)

parser = argparse.ArgumentParser(description="Send files to multiple sftp servers")
parser.add_argument('locations', nargs='*', help="Locations of files/folders to transfer")
parser.add_argument('--user', default='sftpuser', help="Username for sftp")
parser.add_argument('--remote_dir', default='/remote_directory/', help="Remote directory to put the files")

args = parser.parse_args()

with open('config/config.json') as f:
    config = json.load(f)

sftp_servers = config.get('sftp_servers')
sftp_servers_cycle = itertools.cycle(sftp_servers)
private_key_path = config.get('private_key_path')

private_key = paramiko.RSAKey(filename=private_key_path)

def upload_file(server, user, private_key, location, remote_dir):
    # Check both file and directory
    if not os.path.isfile(location) and not os.path.isdir(location):
        msg = f'{location} neither a file nor a directory or does not exist.'
        print(msg)
        logger.error(msg)
        manifest_logger.info(msg)
        sys.exit(1)

    try:
        transport = paramiko.Transport(server)
        transport.connect(username=user, pkey=private_key)
        sftp = transport.open_sftp()

        if os.path.isfile(location):  # if location is a file
            manifest_logger.info(f"Starting to upload {location} to server {server}")
            sftp.put(location, os.path.join(remote_dir, os.path.basename(location)))
            manifest_logger.info(f"Upload of {location} to {server} successful.")
        elif os.path.isdir(location):  # if location is a directory
            for root, dirs, files in os.walk(location):
                for filename in files:
                    local_path = os.path.join(root, filename)
                    remote_path = os.path.join(remote_dir, os.path.basename(local_path))
                    manifest_logger.info(f"Starting to upload {local_path} to server {server}")
                    sftp.put(local_path, remote_path)
                    manifest_logger.info(f"Upload of {local_path} to {server} successful.")

        sftp.close()
        transport.close()
        return (True, location)

    except Exception as e:
        error_msg = f"Failed to transfer {location} to {server}. Error: {str(e)}"
        logger.error(error_msg)
        manifest_logger.info(error_msg)
        return (False, location)


# Start of the Main script
success_count = 0
fail_count = 0

for location in args.locations:
    success, _ = upload_file(sftp_servers_cycle, location)
    if success:
        success_count += 1
    else:
        fail_count += 1

print(
    f"File transfer completed. {success_count} uploads successful, {fail_count} uploads failed. Please check 'logs/sftp_transfers.log' for more details.")