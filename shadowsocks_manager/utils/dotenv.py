#!/usr/bin/env python
"""
Description:
    ssm-dotenv is a command-line utility for administrative tasks.
    It is used to manage the environment variables for the shadowsocks-manager.

Usage:
    ssm-dotenv [-w ENVS ...]

Options:
    [-w ENVS ...]   Write enviaronment variables in KEY=VALUE format for .ssm-env file.
                    The .ssm-env file is used by django settings.

Environment:
    The following environment variables are used by this script to determine the location of the .ssm-env file:

    - SSM_DATA_HOME
    
      If the SSM_DATA_HOME is not set, Django root directory is used as the default location for the .ssm-env file.

Returns:
    None

Example:
    $ ssm-dotenv -w SSM_SECRET_KEY=yourkey SSM_DEBUG=False
"""
import os
import sys
from docopt import docopt


def get_env_file(ssm_data_home):
    env_file = os.path.join(ssm_data_home, '.ssm-env')
    if not os.path.exists(env_file):
        # create the .ssm-env file if it does not exist
        with open(env_file, 'w') as f:
            f.write('')
    return env_file


def main():
    # get SSM_DATA_HOME from environment, or use Django root directory as default
    ssm_data_home = os.getenv('SSM_DATA_HOME') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # create the ssm_data_home directory if it does not exist
    if not os.path.exists(ssm_data_home):
        os.makedirs(ssm_data_home)

    # get the .ssm-env file
    env_file = get_env_file(ssm_data_home)

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
                    print("Updated environment variable '{0}' in .ssm-env file.".format(key))
                else:
                    f.write(line)
            if not key_found:
                f.write('\n' + new_line)
                print("Added environment variable '{0}' to .ssm-env file.".format(key))


if __name__ == "__main__":
    sys.exit(main())