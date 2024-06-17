#!/usr/bin/env python
import os
import sys
import subprocess
import signal


def signal_handler(sig, frame):
    print('{} [{}]: Interrupt received'.format('ssm-uwsgi', os.getpid()))
    sys.exit(255)

signal.signal(signal.SIGINT, signal_handler)


def main():
    """
    Description:
        Call `ssm uwsgi --ini uwsgi.ini` and proxy the rest options.

    Usage:
        ssm-uwsgi [OPTIONS]

    Options:
        OPTIONS     All options are transparently passing to uwsgi.

    Returns:
        None

    Example:
        $ ssm-uwsgi
    """
    return subprocess.call(["ssm", "uwsgi", "--ini", "uwsgi.ini"] + sys.argv[1:])


if __name__ == '__main__':
    sys.exit(main())