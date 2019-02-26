#!/opt/anaconda3/bin/python3
import atexit
import logging
import os
import signal
import sys
import time


log = logging.getLogger(__name__)


class Daemon:
    """A generic daemon class.

    Usage: subclass the daemon class and override the run() method."""

    def __init__(self, pidfile):
        self.pidfile = pidfile
        self.running = False

    def daemonize(self, stdin=None, stderr=None, stdout=None):
        """Deamonize class. UNIX double fork mechanism."""
        stdin = '/dev/null' if not stdin else stdin
        stdout = '/dev/null' if not stdout else stdout
        stderr = '/dev/null' if not stderr else stderr

        log.info("Daemonizing..")
        try:
                pid = os.fork()
                if pid > 0:
                        # exit first parent
                        sys.exit(0)
        except OSError as err:
                sys.stderr.write('fork #1 failed: {0}\n'.format(err))
                sys.exit(1)

        # decouple from parent environment
        os.chdir('/')
        os.setsid()
        os.umask(0)

        # do second fork
        try:
            pid = os.fork()
            if pid > 0:
                # exit from second parent
                sys.exit(0)
        except OSError as err:
            sys.stderr.write('fork #2 failed: {0}\n'.format(err))
            sys.exit(1)

        # redirect standard file descriptors ; skip if debug is True

        sys.stdout.flush()
        sys.stderr.flush()

        # Replace file descriptors for stdin, stdout, and stderr
        with open(stdin, 'rb', 0) as f:
            os.dup2(f.fileno(), sys.stdin.fileno())
        with open(stdout, 'ab', 0) as f:
            os.dup2(f.fileno(), sys.stdout.fileno())
        with open(stderr, 'ab', 0) as f:
            os.dup2(f.fileno(), sys.stderr.fileno())

        # write pidfile
        atexit.register(self.delpid)

        pid = str(os.getpid())
        with open(self.pidfile, 'w+') as f:
                f.write(pid + '\n')

    def delpid(self):
        os.remove(self.pidfile)

    def start(self, stdin=None, stderr=None, stdout=None):
        log.info("Starting Daemon..")
        self.running = True
        # Check for a pidfile to see if the daemon already runs
        try:
            with open(self.pidfile, 'r') as pf:
                pid = int(pf.read().strip())
        except IOError:
            pid = None

        if pid:
            message = "pidfile {0} already exist. Daemon already running?\n"
            log.error(message)
            sys.stderr.write(message.format(self.pidfile))
            sys.exit(1)

        # Start the daemon
        self.daemonize(stdin, stdout, stderr)
        self.run()

    def stop(self):
        """Stop the daemon."""
        self.running = False
        # Get the pid from the pidfile
        try:
            with open(self.pidfile, 'r') as pf:
                pid = int(pf.read().strip())
        except IOError:
            pid = None

        if not pid:
            message = "pidfile {0} does not exist. Daemon not running?\n"
            sys.stderr.write(message.format(self.pidfile))
            return  # not an error in a restart

        # Try killing the daemon process
        try:
            while 1:
                os.kill(pid, signal.SIGTERM)
                time.sleep(0.1)
        except OSError as err:
            e = str(err.args)
            if e.find("No such process") > 0:
                if os.path.exists(self.pidfile):
                    self.delpid()
                else:
                    print(str(err.args))
                    sys.exit(1)

    def restart(self):
        """Restart the daemon."""
        log.info("Restarting Daemon..")
        self.stop()
        self.start()

    def status(self):
        if os.path.isfile(self.pidfile):
            return "This Daemon roams the realm of your system! (It's running)"
        else:
            return "This Daemon has not been summoned. (It's not running)"

    def run(self):
        while self.running:
            continue

if __name__ == '__main__':
    d = Daemon()
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            d.start()
        elif 'stop' == sys.argv[1]:
            d.stop()
        elif 'restart' == sys.argv[1]:
            d.restart()
        elif 'status':
            print(d.status())
        else:
            print("usage: %s start|stop|restart" % sys.argv[0])
            sys.exit(2)
        sys.exit(0)
    else:
        print("usage: %s start|stop|restart" % sys.argv[0])
        sys.exit(2)
