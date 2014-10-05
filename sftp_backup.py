#! /usr/bin/env python

'''
    Simple script to automate encrypted backups.

    Run this script with "-h" argument to see the list of arguments.

    Example:

        ./sftp_backup.py \
        --7zip-command 7z \
        --archive-password Sekrit \
        --hostname 192.168.56.8 \
        --username test \
        --server-password test \
        /usr/share/licenses \
        /etc/resolv.conf \
        /etc/vimrc
'''

import subprocess
import time
import os
import tempfile
import argparse
import pysftp


def compress_directory(directory_to_compress,
                       full_path_to_7zip_executable,
                       archive_password):
    '''
        Compresses given directory with given password and
        places the resulting archive in a temporary directory.

        Returns: full path to the resulting archive.
    '''

    archive_filename = os.path.basename(directory_to_compress) + \
                       '_' + \
                       time.strftime('%Y.%m.%d_%H.%M.%S') + \
                       '.7z'

    print('Archive filename:', archive_filename)

    system_temp_dir = tempfile.gettempdir()

    print('Using temporary directory:', system_temp_dir)

    path_to_archive = os.path.join(system_temp_dir, archive_filename)

    print('Full path to archive will be:', path_to_archive)

    commands = [full_path_to_7zip_executable,
                'a',
                '-t7z',
                path_to_archive,
                directory_to_compress,
                '-mhe',
                '-mx9',
               ]

    if archive_password is not None:
        commands.append('-p' + archive_password)

    print('Running 7zip command:\n' + ' '.join(commands))

    print('='*79)

    try:
        subprocess.check_call(commands, universal_newlines=True)
    except subprocess.CalledProcessError as ex:
        if ex.returncode == 1:
            print('WARNING: 7z exited with warnings, but will continue anyway')
        else:
            raise ex

    print('='*79)

    return path_to_archive


def upload_file(sftp_connection, path_to_local_file, remote_path):
    '''
        Uploads given file to given server connection.
    '''

    print('Uploading "{0}" to remote dir "{1}".'.format(path_to_local_file,
                                                        remote_path))

    with sftp_connection.cd(remote_path):
        sftp_connection.put(path_to_local_file)

    print('Upload seems OK.')


def get_args():
    '''
        Initialize argument parser and return the list of tuples of arguments.
    '''

    parser = argparse.ArgumentParser()
    parser.add_argument('directories',
                        metavar='directory',
                        type=str,
                        nargs='+',
                        help='Full path to the local director(ies) to backup')
    parser.add_argument('--7zip-command',
                        dest='command_7zip',
                        metavar='7zip_executable',
                        type=str,
                        required=True,
                        help='7-Zip command name or path to 7z.exe')
    parser.add_argument('--archive-password',
                        dest='archive_password',
                        metavar='archive_password',
                        type=str,
                        default=None,
                        help='Archive password')
    parser.add_argument('--hostname',
                        dest='sftp_hostname',
                        metavar='sftp_hostname',
                        type=str,
                        required=True,
                        help='SFTP server IP address or hostname')
    parser.add_argument('--port',
                        dest='sftp_port',
                        metavar='sftp_port',
                        type=int,
                        default=22,
                        help='SFTP server port')
    parser.add_argument('--username',
                        dest='sftp_username',
                        metavar='sftp_username',
                        type=str,
                        default=None,
                        help='SFTP server username')
    parser.add_argument('--server-password',
                        dest='sftp_password',
                        metavar='sftp_password',
                        type=str,
                        default='',
                        help='SFTP server password')
    parser.add_argument('--remote-path',
                        dest='remote_path',
                        metavar='remote_path',
                        type=str,
                        default='/',
                        help='Directory on SFTP server to put the archive in')
    args = parser.parse_args()

    return args


def main():
    '''
        Main function.
    '''

    args = get_args()

    print('Connecting to {0}:{1} as "{2}".'.format(args.sftp_hostname,
                                                   args.sftp_port,
                                                   args.sftp_username))

    try:
        sftp_connection = pysftp.Connection(args.sftp_hostname,
                                            port=args.sftp_port,
                                            username=args.sftp_username,
                                            password=args.sftp_password)
    except pysftp.AuthenticationException as ex:
        print('ERROR: Could not log to {0}:{1} as {2}: {3}'.format(
            args.sftp_hostname,
            args.sftp_port,
            args.sftp_username,
            str(ex)))

        return
    except pysftp.paramiko.ssh_exception.SSHException as ex:
        print(str(ex))
        return

    for local_directory in args.directories:
        path_to_archive = compress_directory(local_directory,
                                             args.command_7zip,
                                             args.archive_password)

        upload_file(sftp_connection, path_to_archive, args.remote_path)

        os.remove(path_to_archive)

    sftp_connection.close()


if __name__ == '__main__':
    main()

