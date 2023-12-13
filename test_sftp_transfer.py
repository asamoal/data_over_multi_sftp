import unittest
from unittest.mock import patch, call
from data_over_multi_sftp import upload_file


class TestDataOverMultiSftp(unittest.TestCase):
    @patch('data_over_multi_sftp.upload_file', create=True)
    def test_upload_file(self, mock_upload_file):
        # Assume
        def side_effect(server, user, pkey, location, remote_dir):
            if server == 'localhost:2222':
                return True
            elif server == 'localhost:2223':
                raise Exception('Failed to upload')
            elif server == 'localhost:3333':
                return True

        mock_upload_file.side_effect = side_effect
        locations = ['/Users/leslieasamoa/CrushDrive/fake_data_generator/20231201-1236707lak-account-cords-gen1']
        servers = ['localhost:3333']

        # Action
        for server, location in zip(servers, locations):
            args_to_upload = (server, 'user', 'config/keys/sftp-user-key', location, 'upload/')
            # make sure args_to_upload parameters matches with the ones used in `calls` list
            upload_file(*args_to_upload)

        # Assert
        calls = [call(server, 'user', 'config/keys/sftp-user-key', location, 'upload/') for server, location in
                 zip(servers, locations)]

        # make sure `calls` list parameters matches with the ones used in `args_to_upload`
        mock_upload_file.assert_has_calls(calls)


if __name__ == '__main__':
    unittest.main()