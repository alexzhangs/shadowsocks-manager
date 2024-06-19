#!/usr/bin/env python
import os
import sys
import subprocess
import signal


def signal_handler(sig, frame):
    print('{} [{}]: Interrupt received'.format('ssm-manager', os.getpid()))
    sys.exit(255)

signal.signal(signal.SIGINT, signal_handler)


def main():
    """
    Description:
        Call `ssm python manage.py` and proxy the rest options.

    Usage:
        ssm DJANGO_COMMAND [OPTIONS]

    Options:
        DJANGO_COMMAND     The django management command to be run.
        OPTIONS            All options are transparently passing to django management command.

    Returns:
        None

    Example:
        $ ssm-manage runserver
        $ ssm-manage shell
    """
    return subprocess.call(["ssm", "python", "manage.py"] + sys.argv[1:])


if __name__ == '__main__':
    sys.exit(main())