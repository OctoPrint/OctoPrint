"""
Generic linux daemon base class

Originally from http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/#c35
"""

import os
import signal
import sys
import time


class Daemon:
    """
    A generic daemon class.

    Usage: subclass the daemon class and override the run() method.

    If you want to log the output to someplace different that stdout and stderr,
    also override the echo() and error() methods.
    """

    def __init__(self, pidfile):
        self.pidfile = pidfile

    def _daemonize(self):
        """Daemonize class. UNIX double fork mechanism."""

        self._double_fork()
        self._redirect_io()

        # write pidfile
        pid = str(os.getpid())
        self.set_pid(pid)

    def _double_fork(self):
        try:
            pid = os.fork()
            if pid > 0:
                # exit first parent
                sys.exit(0)
        except OSError as err:
            self.error(f"First fork failed: {str(err)}")
            sys.exit(1)

        # decouple from parent environment
        os.chdir("/")
        os.setsid()
        os.umask(0o002)

        # do second fork
        try:
            pid = os.fork()
            if pid > 0:
                # exit from second parent
                sys.exit(0)
        except OSError as err:
            self.error(f"Second fork failed: {str(err)}")
            sys.exit(1)

    def _redirect_io(self):
        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = open(os.devnull, encoding="utf-8")
        so = open(os.devnull, "a+", encoding="utf-8")
        se = open(os.devnull, "a+", encoding="utf-8")

        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

    def terminated(self):
        self.remove_pidfile()

    def start(self):
        """Start the daemon."""

        # Check for a pidfile to see if the daemon already runs
        pid = self.get_pid()
        if pid:
            self.error(
                "pidfile {} already exist. Is the daemon already running?".format(
                    self.pidfile
                )
            )
            sys.exit(1)

        self.echo("Starting daemon...")

        # Start the daemon
        self._daemonize()
        self.run()

    def stop(self, check_running=True):
        """Stop the daemon."""
        pid = self.get_pid()
        if not pid:
            if not check_running:
                return
            self.error(
                "pidfile {} does not exist. Is the daemon really running?".format(
                    self.pidfile
                )
            )
            sys.exit(1)

        self.echo("Stopping daemon...")

        # Try killing the daemon process
        try:
            while 1:
                os.kill(pid, signal.SIGTERM)
                time.sleep(0.1)
        except OSError as err:
            e = str(err.args)
            if e.find("No such process") > 0:
                self.remove_pidfile()
            else:
                self.error(e)
                sys.exit(1)

    def restart(self):
        """Restart the daemon."""
        self.stop(check_running=False)
        self.start()

    def status(self):
        """Prints the daemon status."""
        if self.is_running():
            self.echo("Daemon is running")
        else:
            self.echo("Daemon is not running")

    def is_running(self):
        """Check if a process is running under the specified pid."""
        pid = self.get_pid()
        if pid is None:
            return False

        try:
            os.kill(pid, 0)
        except OSError:
            try:
                self.remove_pidfile()
            except Exception:
                self.error("Daemon found not running, but could not remove stale pidfile")
            return False
        else:
            return True

    def get_pid(self):
        """Get the pid from the pidfile."""
        try:
            with open(self.pidfile, encoding="utf-8") as pf:
                pid = int(pf.read().strip())
        except (OSError, ValueError):
            pid = None
        return pid

    def set_pid(self, pid):
        """Write the pid to the pidfile."""
        with open(self.pidfile, "w+", encoding="utf-8") as f:
            f.write(str(pid) + "\n")

    def remove_pidfile(self):
        """Removes the pidfile."""
        if os.path.isfile(self.pidfile):
            os.remove(self.pidfile)

    def run(self):
        """You should override this method when you subclass Daemon.

        It will be called after the process has been daemonized by
        start() or restart()."""

        raise NotImplementedError()

    @classmethod
    def echo(cls, line):
        print(line)

    @classmethod
    def error(cls, line):
        print(line, file=sys.stderr)
