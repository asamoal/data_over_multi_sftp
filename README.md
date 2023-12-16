# Data Over Multiple SFTP Project

This Python project is intended to send files over multiple SFTP servers in a round-robin fashion based on a given configuration file.

## Description

This Python script uses the `paramiko` library to establish SFTP connections and transfer files. It accepts multiple arguments specifying the locations of files or folders, the SFTP user, and the remote directory to store the files.

The script sends files to each of the SFTP servers in a round-robin fashion. If 3 locations are provided, each location is sent to a different SFTP server. If 10 locations are given, the same round-robin process is repeated. If a file transfer fails, the script will retry 3 times on the same server before moving to the next server.

## Requirements

- Python 3.11.6
- pip version compatible with Python 3.11.6

You need to have any additional packages installed, which are listed in [`requirements.txt`](./requirements.txt)

## Installation

To install the required dependencies, run the following command in your terminal:

``bash pip install -r requirements.txt``

## Configuration

You need to set up a config.json file in this format:

``json { "sftp_servers": ["localhost:2222", "localhost:3333", "localhost:4444"], "sftp_user": "user", "private_key_path": "config/keys/sftp-user-key", "remote_dir": "upload/", "locations" : ["/path/to/folder1", "/path/to/folder2"] }``

Replace the values with your actual SFTP server addresses and local file paths.

Your private key should be located at the path `"/path/to/private/key"`.

You can also provide the user and remote directory your want to upload to.

## Usage

There are several convenient ways to run this script, let's start with the basics.

If you have provided supporting values in the config.json, navigate to the project folder and execute the following in your terminal (linux/bash works best):

``bash python data_over_multi_sftp.py /path/to/file1 /path/to/file2 ...``

If you have linux with bracket-expansion you could also run a script like this;

``bash python data_over_multi_sftp.py $(echo /path/to/file{1,2,3,4})``

For more advanced and configuration based executions, the config.json can have all the arguments.

``bash python data_over_multi_sftp.py --config_file /path/to/config.json``

All the folders will be expanded and files will be uploaded to your configured destination in a round robin fashion.

## Testing

Tests are written using Python’s built-in `unittest` module. You can run the tests using the following command in your terminal:

``bash python -m unittest``

## Logging

The script logs its activity to two log files named 'sftp_transfers.log' and 'upload_manifest.log'. Log entries include successful file transfers and failures, along with the particular SFTP server involved and any relevant error messages.