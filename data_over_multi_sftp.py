import sys
import paramiko
import os
import argparse
import json
import logging
import time
from collections import deque


class CustomArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write('error: %s\n' % message)
        self.print_help()
        sys.exit(2)


if not os.path.exists('logs'):
    os.makedirs('logs')

logging.basicConfig(filename='logs/sftp_transfers.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

manifest_logger = logging.getLogger('manifest')
manifest_handler = logging.FileHandler('logs/upload_manifest.log')
manifest_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
manifest_logger.addHandler(manifest_handler)
manifest_logger.setLevel(logging.INFO)

# Set up argument parser
parser = CustomArgumentParser(description="Send files to multiple sftp servers")
parser.add_argument('--config_file', default=None, help="Config file path")
parser.add_argument('--user', default=None, help="Optionally overwrite the sftp_user for sftp in the config file")
parser.add_argument('--remote_dir', default=None, help="Optionally overwrite the remote_dir in the config file")
parser.add_argument('locations', nargs='*', help="Locations of files/folders to transfer")

args = parser.parse_args()

config_file_path = args.config_file or 'config/config.json'  # Default config file path is config/config.json

with open(config_file_path) as f:
    config = json.load(f)

max_retries = config.get('max_retries', 3)  # Default is 3
backoff_base = config.get('backoff_base', 10)  # Default is 10

sftp_servers = config.get('sftp_servers')
sftp_user = args.user or config.get('sftp_user')
private_key_path = config.get('private_key_path')
remote_dir = args.remote_dir or config.get('remote_dir')

# Checks for sftp_servers, sftp_user, private_key_path and remote_dir from config and command line
if not sftp_servers or len(sftp_servers) < 2 or not sftp_user or not private_key_path or not remote_dir:
    parser.error("Some required fields are missing or insufficient in the config file or command line. "
                 "Please ensure to provide the 'sftp_servers' with more than one server, "
                 "'sftp_user', 'private_key_path', and 'remote_dir'.")

locations = args.locations or config.get('locations', [])

# Check if locations are provided either in config file or as command-line args
if not locations:
    parser.error("No locations found. Please provide locations either via the config file "
                 "or as command line arguments.")

# Enable our ability to cycle through the SFTP Servers
# Convert sftp_servers to a queue using a deque
sftp_servers_queue = deque(sftp_servers)
private_key = paramiko.RSAKey(filename=private_key_path)


def upload_file(upl_server_address, user, upl_private_key, upl_location, upl_remote_dir,
                upl_max_retries, upl_backoff_base):
    upl_server, upl_port = upl_server_address.split(":")
    upl_port = int(upl_port)

    upl_file_count = 0
    if not os.path.isfile(upl_location) and not os.path.isdir(upl_location):
        msg = f'{upl_location} is neither a file nor a directory or does not exist.'
        print(msg)
        logger.error(msg)
        manifest_logger.info(msg)
        return (False, upl_location, upl_server, upl_port, upl_file_count)

    backoff_penalty = upl_backoff_base
    retries = 0
    while retries < upl_max_retries:
        try:
            logger.info(f'Uploading to SFTP Node:{upl_server} on port:{upl_port} with user: {user}')
            transport = paramiko.Transport((upl_server, upl_port))
            transport.connect(username=user, pkey=upl_private_key)
            sftp = transport.open_sftp_client()

            if os.path.isfile(upl_location):
                manifest_logger.info(f"Starting to upload {upl_location} to server {upl_server}:{upl_port}")
                sftp.put(upl_location, os.path.join(upl_remote_dir, os.path.basename(upl_location)))
                manifest_logger.info(f"Upload of {upl_location} to {upl_server}:{upl_port} successful.")
                upl_file_count += 1

            elif os.path.isdir(upl_location):
                for root, dirs, files in os.walk(upl_location):
                    for filename in files:
                        local_path = os.path.join(root, filename)
                        remote_path = os.path.join(upl_remote_dir, os.path.basename(local_path))
                        manifest_logger.info(f"Starting to upload {local_path} to server {upl_server}:{upl_port}")
                        sftp.put(local_path, remote_path)
                        manifest_logger.info(f"Upload of {local_path} to {upl_server}:{upl_port} successful.")
                        upl_file_count += 1
            sftp.close()
            transport.close()
            return (True, upl_location, upl_server, upl_port, upl_file_count)

        except Exception as e:
            retries += 1
            error_msg = (f"Failed to transfer {upl_location} to {upl_server}:{upl_port}. Retry attempt: {retries}. "
                         f"Applying backoff penalty: {backoff_penalty}. Error: {str(e)}")
            print(f"{error_msg}")
            logger.error(error_msg)
            manifest_logger.info(error_msg)
            time.sleep(backoff_penalty)  # Wait
            backoff_penalty *= retries

    # if reached here, it means all retry attempts have failed
    return (False, upl_location, upl_server, upl_port, upl_file_count)


successful_uploads = []
unsuccessful_uploads = []
total_files = 0

for location in locations:
    print(f"Attempting to send: {location}")
    for _ in range(len(sftp_servers_queue)):  # This will attempt to upload to each SFTP server once
        server_address = sftp_servers_queue[0]  # Get the first server in the queue
        print(f"Allocating server: {server_address} for: {location}")
        success, processed_location, server, port, file_count = upload_file(server_address, sftp_user, private_key,
                                                                            location, remote_dir, max_retries,
                                                                            backoff_base)
        if success:  # If upload was successful, rotate queue and break loop
            sftp_servers_queue.rotate(-1)
            break
        else:  # If upload was not successful, rotate queue and try next server
            sftp_servers_queue.rotate(-1)

    total_files += file_count
    if success:
        successful_uploads.append((processed_location, server, port, file_count))
    else:
        unsuccessful_uploads.append((processed_location, server, port))

print(f"File transfer execution. {len(successful_uploads)} uploads successful to the following servers:")
for location, server, port, file_count in successful_uploads:
    print(f"- {location} containing {file_count} files was successfully uploaded to {server}:{port}")
    print("Please check 'logs/upload_manifest.log' for more details.")
print(f"{len(unsuccessful_uploads)} uploads failed:")
for location, server, port in unsuccessful_uploads:
    print(f"- Uploading {location} to {server}:{port} failed.")
    print("Please check 'logs/sftp_transfers.log' for more details.")
print(f"Total Number of files transferred: {total_files}")
