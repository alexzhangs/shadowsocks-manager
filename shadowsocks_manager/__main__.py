#!/usr/bin/env python
import os
import sys
import subprocess
from docopt import docopt


def main():
    """
    Description:
        Make the proxy call after adding the django root to the python path and changing the current directory to the django root.

    Usage:
        ssm COMMAND [OPTIONS]

    Options:
        COMMAND     The command to be run.
        OPTIONS     All options are transparently passing to the called command.

    Returns:
        None

    Example:
        $ ssm python manage.py runserver
        $ ssm uwsgi --ini uwsgi.ini
        $ ssm celery -A shadowsocks_manager worker -l info
    """
    #docopt(main.__doc__)

    django_root = os.path.dirname(os.path.abspath(__file__))

    # add the django root to the python path to allow django commands to be run from any directory
    if django_root not in sys.path:
        sys.path.insert(0, django_root)

    # change dir to the django root to allow the dir-sensitive commands(such as loaddata) to be run from any directory
    os.chdir(django_root)

 
    # make the proxy call
    return subprocess.call(sys.argv[1:])


if __name__ == '__main__':
    sys.exit(main())