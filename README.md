# Data Over Multiple SFTP Project

This Python project is intended to send files over multiple SFTP servers in a round-robin fashion based on a given configuration file. It employs various error handling and resilience techniques against server failures during the file upload process. 

## Improvements

- Retry Mechanism: If a file upload fails, the script will attempt to upload the same file to the next server in the sequence. The maximum number of retries and the servers in the round-robin sequence can all be adjusted in the configuration file.

- Backoff Penalty: If an upload to a server fails, the script will wait for a certain period (backoff penalty) before the next upload attempt. The duration of the backoff penalty increases with each failed attempt on the same server. The base value for the backoff penalty can be configured in the configuration file.

- Improved Server Selection: The script now ensures that it does not attempt uploads to the same server consecutively, unless it has successfully uploaded on all other servers.

- Better Logging: More comprehensive logging messages have been added for improved debugging visibility.

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

New parameters added to the `config.json` file:

- `max_retries`: The maximum number of times the script should retry an upload to a server before moving onto the next server.

- `backoff_base`: The base number of seconds for the backoff penalty. This value is doubled after each subsequent failed retry on same server.

You need to set up a config.json file in this format:

```json 
{ 
 "backoff_base": 10,
  "locations": [
    "/path/to/folder1",
    "/path/to/folder2",
    "/path/to/folder3"
  ],
  "max_retries": 3,
  "private_key_path": "config/keys/sftp-user-key",
  "remote_dir": "upload/",
  "sftp_servers": [
    "localhost:2222",
    "localhost:3333",
    "localhost:4444"
  ],
  "sftp_user": "user"
}
  ```

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