import paramiko

# Replace with your username
username = 'user'
# Replace with the address of your SFTP server
server = 'localhost'
# Replace with the port of your SFTP server
port = 2222
# Replace with the path to your private key
private_key_path = 'config/keys/sftp-user-key'

private_key = paramiko.RSAKey.from_private_key_file(private_key_path)

try:
    transport = paramiko.Transport((server, port))
    transport.connect(username=username, pkey=private_key)
    sftp = transport.open_sftp_client()
    print(sftp.listdir())  # Prints the files in the root directory on the server
    sftp.close()
    transport.close()
    print(f"Successfully connected to {server} on port {port}")
except Exception as e:
    print(f"Failed to connect to {server} on port {port}. Error: {str(e)}")