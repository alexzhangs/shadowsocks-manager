#!/usr/bin/env python
"""
Description:
    ssm-dotenv is a command-line utility for administrative tasks.
    It is used to manage the environment variables for the shadowsocks-manager.

Usage:
    ssm-dotenv [-w ENVS ...]

Options:
    [-w ENVS ...]   Write enviaronment variables in KEY=VALUE format for .env file.
                    The .env file is used by django settings.

Returns:
    None

Example:
    ssm-dotenv -w SSM_SECRET_KEY=yourkey SSM_DEBUG=False
"""
import os
import sys
from docopt import docopt


def get_env_file():
    django_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(django_root, '.env')


def main():
    env_file = get_env_file()

    arguments = docopt(__doc__)

    if not arguments["ENVS"]:
        with open(env_file, 'r') as f:
            lines = f.readlines()
        for line in lines:
            print(line.strip())

    envs = arguments["ENVS"]
    for env in envs:
        pair = env.split('=', 1)
        key = pair[0]
        try:
            value = pair[1]
        except IndexError:
            raise ValueError(f"Invalid format for environment variable '{env}'.")
        
        new_line = key + '=' + value + '\n'

        with open(env_file, 'r') as f:
            lines = f.readlines()

        with open(env_file, 'w') as f:
            key_found = False
            for line in lines:
                if line.startswith(key + '='):
                    f.write(new_line)
                    key_found = True
                    print(f"Updated environment variable '{key}' in .env file.")
                else:
                    f.write(line)
            if not key_found:
                f.write('\n' + new_line)
                print(f"Added environment variable '{key}' to .env file.")


if __name__ == "__main__":
    sys.exit(main())