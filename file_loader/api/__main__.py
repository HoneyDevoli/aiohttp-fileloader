"""
The REST API service that can work with files
"""
import argparse
import logging
import os
import pathlib

import pwd
from sys import argv

from aiohttp.web import run_app
from aiomisc import bind_socket
from aiomisc.log import LogFormat, basic_config
from configargparse import ArgumentParser
from setproctitle import setproctitle

from file_loader.api.app import create_app
from file_loader.utils.argparse import clear_environ, positive_int,\
    validate, create_dirs

ENV_VAR_PREFIX = 'FILE_LOADER_'
BASE_STORAGE_DIR \
    = pathlib.Path(__file__).resolve().parent.parent.parent / 'storage'

parser = ArgumentParser(
    auto_env_var_prefix=ENV_VAR_PREFIX, allow_abbrev=False,
    formatter_class=argparse.ArgumentDefaultsHelpFormatter
)
parser.add_argument('--user', required=False, type=pwd.getpwnam,
                    help='Change process UID')

group = parser.add_argument_group('API Options')
group.add_argument('--api-address', default='0.0.0.0',
                   help='IPv4/IPv6 address API server would listen on')
group.add_argument('--api-port', type=positive_int, default=8081,
                   help='TCP port API server would listen on')

group = parser.add_argument_group('Logging options')
group.add_argument('--log-level', default='info',
                   choices=('debug', 'info', 'warning', 'error', 'fatal'))
group.add_argument('--log-format', choices=LogFormat.choices(),
                   default='color')

group = parser.add_argument_group('Daemon options')
group.add_argument('--storage',
                   default=BASE_STORAGE_DIR,
                   type=validate(pathlib.Path,),
                   help='Directory for storage loaded files')


def main():
    args = parser.parse_args()

    # After reading the system variables need to clear them
    clear_environ(lambda i: i.startswith(ENV_VAR_PREFIX))

    # So that the logs do not block the main thread during write operations
    basic_config(args.log_level, args.log_format, buffered=True)

    create_dirs(args.daemon_storage)

    # Socket is allocated for ability change the OS user
    sock = bind_socket(address=args.api_address, port=args.api_port,
                       proto_name='http')
    if args.user is not None:
        logging.info('Changing user to %r', args.user.pw_name)
        os.setgid(args.user.pw_gid)
        os.setuid(args.user.pw_uid)

    # Give the process a name
    setproctitle(os.path.basename(argv[0]))

    app = create_app()
    app['storage_path'] = args.daemon_storage

    run_app(app, sock=sock)


if __name__ == '__main__':
    main()
