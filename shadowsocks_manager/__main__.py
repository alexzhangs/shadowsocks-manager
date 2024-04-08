#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
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

    django_root = os.path.dirname(os.path.abspath(__file__))

    # add the django root to the python path to allow django commands to be run from any directory
    if django_root not in sys.path:
        sys.path.insert(0, django_root)

    # change dir to the django root to allow the dir-sensitive commands(such as loaddata) to be run from any directory
    os.chdir(django_root)

    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()