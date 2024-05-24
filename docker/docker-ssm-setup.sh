#!/usr/bin/env bash

#? Description:
#?   This script is called by the entrypoint script of the shadowsocks-manager container.
#?   It will:
#?   - Setup the shadowsocks-manager (if the setup done file does not exist):
#?     - Copy the .ssm-env file if it does not exist
#?     - Setup the required directories
#?     - Run the ssm-setup script
#?     - Create the setup done file
#?
#?   This script should be called by SSM_USER.
#?
#? Usage:
#?   docker-ssm-setup.sh [SSM_SETUP_OPTIONS]
#?   docker-ssm-setup.sh [-h]
#?
#? Options:
#?   [SSM_SETUP_OPTIONS]
#?
#?   Options are the same as the ssm-setup script.
#?   If any option is provided, the options will pass along with the default options to the ssm-setup script.
#?   The default options are: `-c -m -l -u admin -p passw0rd`.
#?
#?   [-h]
#?
#?   This help.
#?
#? Environment:
#?   The following environment variables are used by this script:
#?
#?   - SSM_DATA_HOME
#?
#?     Required.
#?     Set the base directory for .ssm-env file and the Django database and static files.
#?
#? File:
#?   The following files conditionally created by this script:
#?
#?   - $SSM_DATA_HOME/.ssm-setup-done
#?
#?     This file is created after the initial setup.
#?     The initial setup will be skipped if this file exists.
#?

# exit on any error
set -e -o pipefail

function usage () {
    awk '/^#\?/ {sub("^[ ]*#\\?[ ]?", ""); print}' "$0" \
        | awk '{gsub(/^[^ ]+.*/, "\033[1m&\033[0m"); print}'
}

function main () {
    if [[ $1 == -h ]]; then
        usage
        return
    fi

    declare ssm_setup_done_file="$SSM_DATA_HOME/.ssm-setup-done"

    # Skip the initial setup if the ssm setup done file exist
    if [[ -f $ssm_setup_done_file ]]; then
        echo "INFO: The initial setup had been done before."
        return
    fi

    # Copy the .ssm-env file to the SSM_DATA_HOME if it does not exist
    cp -n /shadowsocks-manager/.ssm-env-example "$SSM_DATA_HOME/.ssm-env"

    # Create the required directories
    mkdir -p "$SSM_DATA_HOME/db" "$SSM_DATA_HOME/static"

    # Set the default options
    declare -a default_options=(-c -m -l -u admin -p passw0rd)

    # Run the initial setup, the explicit options may override the default options
    ssm-setup "${default_options[@]}" "$@"

    # Create the ssm setup done file
    touch "$ssm_setup_done_file"
}

main "$@"

exit
