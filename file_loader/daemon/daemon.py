import atexit
import os
import signal
import sys
import errno
from abc import ABC, abstractmethod
from pathlib import Path


class PidFile:
    """Class for work with pid file.
    :param file_path: the pid`s file path """
    def __init__(self, file_path: Path):
        self.file_path = file_path

    def load(self) -> int:
        """Loaded pid from file.
        :raise FileNotFoundError when pid file by file_path not found
        :raise ValueError when pid has incorrect format
        :return: pid from file
        """
        with open(self.file_path, 'r') as pf:
            pid = pf.read().strip()
            if not pid.isdigit():
                raise ValueError('Pid file does not contain a number')

            pid = int(pid)
            if not pid > 0:
                raise ValueError('Pid must be greater than 0')

            return pid

    def save(self, value: int) -> None:
        """Save pid in file.
        :param value: the pid that should be save in file
        :raise ValueError when pid has incorrect format
        """
        if not value > 0:
            raise ValueError('Cannot be negative')

        with open(self.file_path, 'w') as f:
            f.write(str(value))

    def remove(self) -> None:
        """Delete pid file."""
        if self.is_file_exist():
            os.remove(self.file_path)

    def is_file_exist(self) -> bool:
        """Checking that the file by the path is exist."""
        return os.path.exists(self.file_path)


class Process:
    """Class for working with unix process.
    :param file_path: the pid`s file path which the process id
    will be place"""
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.pid_file = PidFile(file_path)

    def is_running(self) -> bool:
        """Checking process status.
        :raise FileNotFoundError when pid file by file_path not found
        :return: true then the process is running
        """
        if self.pid_file.is_file_exist():
            pid = self.pid_file.load()
            if not os.path.exists(f'/proc/{pid}'):
                self.pid_file.remove()
                return False
        else:
            return False

        return True

    def stop(self) -> None:
        """Try killing the daemon process by id.
        :raise FileNotFoundError when pid file by file_path not found
        :raise ValueError when pid has incorrect format"""
        pid = self.pid_file.load()
        os.kill(pid, signal.SIGTERM)

    def save_pid(self) -> None:
        """Save current pid in file."""
        pid = os.getpid()
        self.pid_file.save(pid)

    def remove_pid(self):
        """Remove file with pid."""
        self.pid_file.remove()

    def get_pid(self):
        """Load pid from file.
        :raise FileNotFoundError when pid file by file_path not found"""
        self.pid_file.load()

    @staticmethod
    def fork() -> int:
        """Fork current process.
        :raise OSError when an error occurred during the fork process
        :return: return new pid of the child process
        """
        pid = os.fork()
        if pid > 0:
            # exit from parent
            sys.exit(0)

        return pid


class AbstractDaemon(ABC):
    """A generic daemon class. For use subclass should override
     the run() method.
    :param storage: working directory for daemon
    :param pid_file_name: the name of the pid file that will store the
        process ID
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
        self.process = Process(self.storage / pid_file_name)

        for k in kwargs.keys():
            setattr(self, k, kwargs[k])

    def daemonize(self) -> None:
        """Daemonize class. UNIX double fork mechanism."""
        try:
            Process.fork()
        except OSError as err:
            sys.stderr.write(f'fork #1 failed: {err}')
            sys.exit(1)

        # decouple from parent environment
        os.chdir(self.storage)
        os.setsid()
        os.umask(0)

        # do second fork
        try:
            Process.fork()
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

        atexit.register(self.process.remove_pid)

        self.process.save_pid()

    def start(self) -> None:
        """Start the daemon."""
        if self.process.is_running():
            sys.stderr.write("Daemon already running\n")
            sys.exit(1)
        else:
            self.daemonize()
            self.run()

    def stop(self) -> None:
        """Stop the daemon.
        :raise OSError: process termination error
        """
        try:
            if self.process.is_running():
                self.process.stop()
        except FileNotFoundError:
            sys.stderr.write(f'Pid file in storage \'{self.storage}\' does not'
                             f' exist. Daemon not running?\n')
            sys.exit(1)
        except OSError as err:
            if err.errno == errno.ESRCH:
                # ESRCH == No such process
                sys.stderr.write('The daemon has already stopped')
                sys.exit(1)
            elif err.errno == errno.EPERM:
                # EPERM clearly means there's a process to deny access to
                sys.stderr.write(f'Error stop daemon with '
                                 f'id {self.process.get_pid()}. Deny access.')
                sys.exit(1)
            else:
                raise

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
