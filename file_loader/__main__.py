import argparse
import asyncio
import logging
import os
import pathlib
import pwd

from aiohttp.web import run_app
from aiomisc import bind_socket
from aiomisc.log import wrap_logging_handler
from configargparse import ArgumentParser
from setproctitle import setproctitle

from file_loader.api.app import create_app
from file_loader.utils.argparse import clear_environ, positive_int, \
    validate
from file_loader.daemon import AbstractDaemon

ENV_VAR_PREFIX = 'FILE_LOADER_'
BASE_STORAGE_DIR \
    = pathlib.Path(__file__).resolve().parent.parent / 'file_loader_storage'

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
group.add_argument('--log-level', default='INFO',
                   choices=('DEBUG', 'INFO', 'WARNING', 'ERROR', 'FATAL'))

group = parser.add_argument_group('Daemon options')
group.add_argument('--working_directory',
                   default=BASE_STORAGE_DIR,
                   type=validate(pathlib.Path),
                   help='Directory for storage daemon files')
group.add_argument('--status', default='start',
                   choices=('start', 'stop', 'restart',))


class FileLoaderDaemon(AbstractDaemon):
    def init_logger(self):
        loop = asyncio.get_event_loop()

        handler = logging.FileHandler(
            self.working_directory / 'file_loader.log')
        handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(message)s'))
        handler = wrap_logging_handler(
            handler=handler,
            buffer_size=1024,
            flush_interval=0.3,
            loop=loop,
        )
        logging.basicConfig(level=self.log_level, handlers=[handler, ])

    def run(self):
        self.init_logger()
        logger = logging.getLogger(__class__.__name__)

        # Socket is allocated for ability change the OS user
        try:
            sock = bind_socket(address=self.api_address, port=self.api_port,
                               proto_name='http')
        except OSError as e:
            logger.exception(e)
            exit(1)

        if self.user is not None:
            logger.info('Changing user to %r', self.user.pw_name)
            os.setgid(self.user.pw_gid)
            os.setuid(self.user.pw_uid)

        app = create_app()
        app['storage_path'] = self.storage

        run_app(app, sock=sock)


def main():
    args = parser.parse_args()

    # After reading the system variables need to clear them
    clear_environ(lambda i: i.startswith(ENV_VAR_PREFIX))

    # Create daemon storage dir
    args.working_directory.mkdir(parents=True, exist_ok=True)

    # Give the process a name
    setproctitle('file-loader-daemon')

    daemon = FileLoaderDaemon(args.working_directory, kwargs=args.__dict__)

    if 'start' == args.status:
        print('Daemon starting..')
        daemon.start()
    elif 'stop' == args.status:
        print('Daemon stopping..')
        daemon.stop()
        print('Daemon stopped!')
    elif 'restart' == args.status:
        print('Daemon restarting..')
        daemon.restart()


if __name__ == "__main__":
    main()
