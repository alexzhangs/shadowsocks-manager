#!/usr/bin/env python
import os
import sys
import subprocess
import signal


def signal_handler(sig, frame):
    print('{} [{}]: Interrupt received'.format('ssm-celery', os.getpid()))
    sys.exit(255)

signal.signal(signal.SIGINT, signal_handler)


def main():
    """
    Description:
        Call `ssm celery -A shadowsocks_manager` and proxy the rest options.

    Usage:
        ssm-celery [OPTIONS]

    Options:
        OPTIONS     All options are transparently passing to celery.

    Returns:
        None

    Example:
        $ ssm-celery worker -l info
        $ ssm-celery beat -l info
    """
    return subprocess.call(["ssm", "celery", "-A", "shadowsocks_manager"] + sys.argv[1:])


if __name__ == '__main__':
    sys.exit(main())