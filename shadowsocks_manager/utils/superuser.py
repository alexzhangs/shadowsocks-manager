#!/usr/bin/env python
"""
Description:
    ssm-superuser is a command-line utility for administrative tasks.
    It is used to manage the superuser account for the shadowsocks-manager.

Usage:
    ssm-superuser --username USERNAME --password PASSWORD [--email EMAIL]

Options:
    -u --username=USERNAME     Username for the superuser account.
    -p --password=PASSWORD     Password for the superuser account.
    -e --email=EMAIL           Email for the superuser account.

Examples:
    ssm-superuser -u admin -p admin123 -e admin@example.com
"""
import os
import sys
from docopt import docopt


def create_superuser(username, password, email):
    # prefix package name to allow being called outside of django environment
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shadowsocks_manager.shadowsocks_manager.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    django_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # add the django root to the python path to allow django commands to be run from any directory
    if django_root not in sys.path:
        sys.path.insert(0, django_root)

    import django
    django.setup()

    from django.contrib.auth.models import User
    User.objects.filter(username=username).delete()
    User.objects.create_superuser(username, email, password)

    print(f"Superuser '{username}' created successfully.")


def main():
    arguments = docopt(__doc__)

    username = arguments["--username"]
    password = arguments["--password"]
    email = arguments["--email"]

    create_superuser(username, password, email)

            
if __name__ == "__main__":
    main()