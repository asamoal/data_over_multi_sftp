import sys
import paramiko
import os
import argparse
import itertools
import json
import logging

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

def upload_file(server_address, user, private_key, location, remote_dir):
    server, port = server_address.split(":")
    port = int(port)
    file_count = 0
    if not os.path.isfile(location) and not os.path.isdir(location):
        msg = f'{location} is neither a file nor a directory or does not exist.'
        print(msg)
        logger.error(msg)
        manifest_logger.info(msg)
        return (False, location, server, port, file_count)

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
        error_msg = f"Failed to transfer {location} to {server}:{port}. Error: {str(e)}"
        logger.error(error_msg)
        manifest_logger.info(error_msg)
        return (False, location, server, port, file_count)

successful_uploads = []
unsuccessful_uploads = []
total_files = 0

for location in args.locations:
    success, processed_location, server, port, file_count = upload_file(next(sftp_servers_cycle), args.user, private_key, location, args.remote_dir)
    total_files += file_count
    if success:
        successful_uploads.append((processed_location, server, port, file_count))
    else:
        unsuccessful_uploads.append((processed_location, server, port))

print(f"File transfer execution. {len(successful_uploads)} uploads successful to the following servers:")
for location, server, port, file_count in successful_uploads:
    print(f"- {location} containing {file_count} files was successfully uploaded to {server}:{port}")
print(f"{len(unsuccessful_uploads)} uploads failed:")
for location, server, port in unsuccessful_uploads:
    print(f"- Uploading {location} to {server}:{port} failed.")
print(f"Total Number of files transferred: {total_files}")
print("Please check 'logs/sftp_transfers.log' for more details.")