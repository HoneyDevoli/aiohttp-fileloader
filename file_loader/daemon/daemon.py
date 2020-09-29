import atexit
import os
import signal
import sys
import errno
from abc import ABC, abstractmethod
from pathlib import Path


def _fork():
    pid = os.fork()
    if pid > 0:
        # exit from parent
        sys.exit(0)

    return pid


class AbstractDaemon(ABC):
    """A generic daemon class. For use subclass should override
     the run() method
    :param storage: working directory for daemon
    :param pid_file_name: the pid`s file name which the daemon process id
    will be place
    :param stdin: new place for stdin
    :param stdout: new place for stdout
    :param stderr: new place for stderr
    :param kwargs: parameters to be used in the run() method
    """
    def __init__(self,
                 storage: Path,
                 pid_file_name: str = 'daemon.pid',
                 stdin: str = '/dev/null',
                 stdout: str = '/dev/null',
                 stderr: str = '/dev/null',
                 kwargs=None):
        if not kwargs:
            kwargs = {}

        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.storage = storage
        self.pid_file = self.storage / pid_file_name

        for k in kwargs.keys():
            setattr(self, k, kwargs[k])

    def daemonize(self) -> None:
        """Daemonize class. UNIX double fork mechanism."""
        try:
            _fork()
        except OSError as err:
            sys.stderr.write(f'fork #1 failed: {err}')
            sys.exit(1)

        # decouple from parent environment
        os.chdir(self.storage)
        os.setsid()
        os.umask(0)

        # do second fork
        try:
            _fork()
        except OSError as err:
            sys.stderr.write(f'fork #2 failed: {err}')
            sys.exit(1)

        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = open(self.stdin, 'r')
        so = open(self.stdout, 'a+')
        se = open(self.stderr, 'a+')
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        # write pid_file
        atexit.register(self.del_pid)

        pid = str(os.getpid())
        with open(self.pid_file, 'w+') as f:
            f.write(pid + '\n')

    def del_pid(self) -> None:
        """Delete pid file"""
        if os.path.exists(self.pid_file):
            os.remove(self.pid_file)

    def start(self) -> None:
        """Start the daemon."""

        # Check for a pid_file to see if the daemon already runs\
        if os.path.exists(self.pid_file):
            sys.stderr.write(f"pid_file {self.pid_file} already exist. "
                             f"Daemon already running?\n")
            sys.exit(1)
        else:
            self.daemonize()
            self.run()

    def stop(self):
        """Stop the daemon.
            :raise OSError: process termination error
        """

        # Get the pid from the pid_file
        try:
            with open(self.pid_file, 'r') as pf:
                pid = int(pf.read().strip())
        except FileNotFoundError:
            sys.stderr.write(f"pid file {self.pid_file} does not exist."
                             f" Daemon not running?\n")
            sys.exit(1)
        else:
            # Try killing the daemon process
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError as err:
                if err.errno == errno.ESRCH:
                    # ESRCH == No such process
                    self.del_pid()
                    sys.exit(1)
                elif err.errno == errno.EPERM:
                    # EPERM clearly means there's a process to deny access to
                    sys.stderr.write('Error stop daemon with id {}.'
                                     ' Deny access'.format(pid))
                    sys.exit(1)
                else:
                    raise
            else:
                self.del_pid()

    def restart(self):
        """Restart the daemon."""
        self.stop()
        self.start()

    @abstractmethod
    def run(self) -> None:
        """You should override this method in your subclass Daemon.
        It will be called after the process has been daemonized by
        start() or restart().
        """
        ...
