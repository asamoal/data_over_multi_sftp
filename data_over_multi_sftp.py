import sys
import paramiko
import os
import argparse
import itertools
import json
import logging


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

sftp_servers = config.get('sftp_servers')
sftp_user = args.user or config.get('sftp_user')
private_key_path = config.get('private_key_path')
remote_dir = args.remote_dir or config.get('remote_dir')

# Checks for sftp_servers, sftp_user, private_key_path and remote_dir from config and command line
if not sftp_servers or len(sftp_servers) < 2 or not sftp_user or not private_key_path or not remote_dir:
    parser.error("Some required fields are missing or insufficient in the config file or command line. "
                 "Please ensure to provide the 'sftp_servers' with more than one server, "
                 "'sftp_user', 'private_key_path', and 'remote_dir'.")

locations = config.get('locations', [])

# Check if locations are provided either in config file or as command-line args
if not locations:
    locations = args.locations

if not locations:
    parser.error("No locations found. Please provide locations either via the config file "
                 "or as command line arguments.")

# Enable our ability to cycle through the SFTP Servers
sftp_servers_cycle = itertools.cycle(sftp_servers)
private_key = paramiko.RSAKey(filename=private_key_path)


def upload_file(server_address, user, private_key, location, remote_dir, max_retries=3):
    server, port = server_address.split(":")
    port = int(port)
    file_count = 0
    if not os.path.isfile(location) and not os.path.isdir(location):
        msg = f'{location} is neither a file nor a directory or does not exist.'
        print(msg)
        logger.error(msg)
        manifest_logger.info(msg)
        return (False, location, server, port, file_count)

    retries = 0
    while retries < max_retries:
        try:
            logger.info(f'Uploading to SFTP Node:{server} on port:{port} with user: {user}')
            transport = paramiko.Transport((server, port))
            transport.connect(username=user, pkey=private_key)
            sftp = transport.open_sftp_client()

            if os.path.isfile(location):
                manifest_logger.info(f"Starting to upload {location} to server {server}:{port}")
                sftp.put(location, os.path.join(remote_dir, os.path.basename(location)))
                manifest_logger.info(f"Upload of {location} to {server}:{port} successful.")
                file_count += 1

            elif os.path.isdir(location):
                for root, dirs, files in os.walk(location):
                    for filename in files:
                        local_path = os.path.join(root, filename)
                        remote_path = os.path.join(remote_dir, os.path.basename(local_path))
                        manifest_logger.info(f"Starting to upload {local_path} to server {server}:{port}")
                        sftp.put(local_path, remote_path)
                        manifest_logger.info(f"Upload of {local_path} to {server}:{port} successful.")
                        file_count += 1
            sftp.close()
            transport.close()
            return (True, location, server, port, file_count)

        except Exception as e:
            retries += 1
            error_msg = f"Failed to transfer {location} to {server}:{port}. Retry attempt: {retries}. Error: {str(e)}"
            logger.error(error_msg)
            manifest_logger.info(error_msg)

    # if reached here, it means all retry attempts have failed
    return (False, location, server, port, file_count)


successful_uploads = []
unsuccessful_uploads = []
total_files = 0

for location in locations:
    success, processed_location, server, port, file_count = upload_file(next(sftp_servers_cycle), args.user,
                                                                        private_key, location, args.remote_dir)
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
