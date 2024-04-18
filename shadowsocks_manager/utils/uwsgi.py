#!/usr/bin/env python
import sys
import subprocess


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