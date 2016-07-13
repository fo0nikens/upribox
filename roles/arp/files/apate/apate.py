from lib import daemon_app
from daemon import runner

import logging
import sys
import signal
import lockfile
import os
import json

CONFIG_FILE = "/etc/apate/config.json"
CONFIG_OPTIONS = ('logfile', 'pidfile', 'interface', 'stderr', 'stdout')


def main():

    # check if run as root
    if os.geteuid() != 0:
        print "This daemon needs to be run as root"
        sys.exit(1)

    # parse configuration file
    try:
        with open(CONFIG_FILE) as config:
            data = json.load(config)
    except ValueError as ve:
        print "Could not parse the configuration file"
        print str(ve)
        sys.exit(3)
    except IOError as ioe:
        print "An error occurred while trying to open the configuration file"
        print str(ioe)
        sys.exit(4)

    if not all(val in data for val in CONFIG_OPTIONS):
        print "The configuration file does not include all necessary options"
        sys.exit(2)

    # set up logger for daemon
    logger = logging.getLogger("DaemonLog")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler = logging.FileHandler(data['logfile'])
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # catch error which could arise during initialisation
    try:
        # dapp = daemon_app.HolisticDaemonApp(logger, str(data['interface']), data['pidfile'], data['stdout'], data['stderr'])
        dapp = daemon_app.SelectiveDaemonApp(logger, str(data['interface']), data['pidfile'], data['stdout'], data['stderr'])
    except Exception as e:
        logger.error("An error happened during initialsising the daemon process - terminating process")
        logger.exception(e)
        sys.exit(1)

    daemon_runner = runner.DaemonRunner(dapp)
    # don't close logfile
    daemon_runner.daemon_context.files_preserve = [handler.stream]
    # start cleanup routine when stopping the daemon
    daemon_runner.daemon_context.signal_map[signal.SIGTERM] = dapp.exit

    # command daemon
    try:
        daemon_runner.do_action()
    except runner.DaemonRunnerError as dre:
        print str(dre)
    except lockfile.LockTimeout as lt:
        print str(lt)
    except Exception:
        # log stacktrace of exceptions that should not occur to logfile
        logger.exception("Exception at do_action()")

        # runner only catches AlreadyLocked, which is not thrown if a timeout was specified other than None or 0
        # Following is thrown otherwise and slips through:
        # LockTimeout: Timeout waiting to acquire lock for /var/run/apate/apate.pid
        # though this should not be logged as an exception

        # restart fails if timeout is set to 0 or None

if __name__ == "__main__":
    main()
