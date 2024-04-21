#!/usr/bin/env python
"""
Description:
    ssm-createsuperuser is a command-line utility for administrative tasks.
    It is used to manage the superuser account for the shadowsocks-manager.

Usage:
    ssm-createsuperuser --username USERNAME --password PASSWORD [--email EMAIL]

Options:
    -u --username=USERNAME     Username for the superuser account.
    -p --password=PASSWORD     Password for the superuser account.
    -e --email=EMAIL           Email for the superuser account.

Returns:
    None

Example:
    ssm-createsuperuser -u admin -p admin123 -e admin@example.com
"""
import os
import sys
from docopt import docopt


def create_superuser(username, password, email):
    # prefix package name to allow being called outside of django environment
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shadowsocks_manager.shadowsocks_manager.settings")

    django_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # add the django root to the python path to allow django commands to be run from any directory
    if django_root not in sys.path:
        sys.path.insert(0, django_root)

    import django
    django.setup()

    from django.contrib.auth.models import User
    User.objects.filter(username=username).delete()
    User.objects.create_superuser(username, email, password)

    print("Superuser '{username}' created successfully.")


def main():
    arguments = docopt(__doc__)

    username = arguments["--username"]
    password = arguments["--password"]
    email = arguments["--email"]

    create_superuser(username, password, email)

            
if __name__ == "__main__":
    sys.exit(main())