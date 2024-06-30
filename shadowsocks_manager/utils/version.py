#!/usr/bin/env python
"""
Description:
    ssm-version is a command-line utility for administrative tasks.
    It's used to show the version and to maintain the build number of the shadowsocks-manager.

Usage:
    ssm-version
    ssm-version [--full]
    ssm-version [--get-build]
    ssm-version [--set-build]

Options:
    --full          Show the full version of the package.
    --get-build     Get the build number of the package.
    --set-build     Set the build number of the package.

Returns:
    None

Example:
    $ ssm-version
"""
import os
import sys
import signal
from datetime import datetime
import subprocess
from docopt import docopt

try:
    from shadowsocks_manager import __version__, __build__
except ImportError:
    from shadowsocks_manager.shadowsocks_manager import __version__, __build__


def signal_handler(sig, frame):
    print('{} [{}]: Interrupt received'.format('ssm-version', os.getpid()))
    sys.exit(255)

signal.signal(signal.SIGINT, signal_handler)


def set_buildno(build, version_file):
    """
    Set the build number in the version file.
    An existing line starting with '__build__ =' will be replaced with the new build number.
    A new line will be added if the line does not exist.
    If the build number is None or empty, it's set as a empty string.
    """
    if build is None:
        build = ''

    found = False
    with open(version_file, 'r') as f:
        lines = f.readlines()

    new_line = '__build__ = "{}"\n'.format(build)
    with open(version_file, 'w') as f:
        for line in lines:
            if line.startswith('__build__ ='):
                f.write(new_line)
                found = True
                print("{}: {}".format(version_file, build))
            else:
                f.write(line)
    return found


def get_buildno():
    """
    Get the build number by checking the git repository.

    Build number format: {short_hash}[-{timestamp}]
        - short_hash:   the short hash of the commit
        - timestamp:    the timestamp of the build, which is appended if the working directory is dirty
    """
    try:
        # Check if inside a git work tree
        with open(os.devnull, 'w') as devnull:
            is_git_repo = subprocess.check_output(['/usr/bin/git', 'rev-parse', '--is-inside-work-tree'], stderr=devnull).strip().decode('utf-8')
        if is_git_repo != 'true':
            return ''

        # get the build information from git commit
        build = subprocess.check_output(['/usr/bin/git', 'rev-parse', '--short', 'HEAD']).strip().decode('utf-8')

        # if the working directory is dirty, append timestamp to the build information
        if subprocess.check_output(['/usr/bin/git', 'status', '--porcelain']).strip().decode('utf-8'):
            ts = None
            try:
                from datetime import timezone
                ts = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M')
            except ImportError:
                ts = datetime.utcnow().strftime('%Y%m%d-%H%M')
            return '{}-{}'.format(build, ts)
        else:
            return '{}'.format(build)
    except Exception:
        return ''


def get_version(full=False):
    """
    Get the version of the package.

    Version format: v{version}
    Full version format: v{version}[-{build}]

        - version: the package version
            - The {package}.__version__ is always hornored.
            - The package building process should be responsible for updating the {package}.__version__.
            - For dev environment, merging the master branch back should update the {package}.__version__.

        - build: the package build number
            - First try to get the build number from the {package}.__build__ (for package distribution).
            - If failed fall back to use the git repository (for dev environment).
            - The package building process should be responsible for updating the {package}.__build__.
    """
    version = 'v{}'.format(__version__ or '0.0.0')

    if full:
        build = __build__ or get_buildno()
        if build:
            version = '{}-{}'.format(version, build)

    return version


def get_version_file():
    django_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(django_root, 'shadowsocks_manager/__init__.py')


def main():
    arguments = docopt(__doc__)

    if not any(arguments.values()):
        print(get_version())
    elif arguments['--full']:
        print(get_version(full=True))
    elif arguments['--get-build']:
        print(get_buildno())
    elif arguments['--set-build']:
        build = get_buildno()
        version_file = get_version_file()
        set_buildno(build, version_file)


if __name__ == '__main__':
    sys.exit(main())