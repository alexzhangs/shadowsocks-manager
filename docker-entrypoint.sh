#!/usr/bin/env bash

#? Description:
#?   This script is the entrypoint for the shadowsocks-manager container.
#?   It will:
#?   - Setup the shadowsocks-manager (if the setup done file does not exist):
#?     - Copy the .ssm-env file
#?     - Setup the required directories
#?     - Run the ssm-setup script
#?     - Create the setup done file
#?   - Start the uWSGI and celery services
#?   - Start the nginx service
#?
#?   This script should be called by user root.
#?
#? Usage:
#?   docker-entrypoint.sh [SSM_SETUP_OPTIONS]
#?
#? Options:
#?   [SSM_SETUP_OPTIONS]
#?
#?   Options are the same as the ssm-setup script.
#?   If any option is provided, the options will pass along with the default options to the ssm-setup script.
#?   The default options are:
#?
#?     -c -m -l
#?     -u admin -p passw0rd
#?
#? Environment:
#?   The following environment variables are used by this script and being set by the Dockerfile:
#?
#?   - SSM_USER
#?
#?     Required.
#?     Set the non-root user to run the ssm-setup.sh script.
#?     The user should exist in the container.
#?
#?   - SSM_DATA_HOME
#?
#?     Required.
#?     Set the base directory for .ssm-env file and the Django database and static files.
#?     The path should exist in the container and should be writable by the SSM_USER.
#?     It should be mounted as a volume in the container while running the docker image.
#?
#? Example:
#?   # for the development environment
#?   $ docker-entrypoint.sh
#?
#?   # for the production environment
#?   $ docker-entrypoint.sh -e SSM_SECRET_KEY=yourkey -e SSM_DEBUG=False -u admin -p yourpassword -M admin@yourdomain.com
#?
function main () {

    # Check if the SSM_USER and SSM_DATA_HOME are set

    if [[ -z $SSM_USER ]]; then
        echo "SSM_USER is not set."
        exit 1
    fi

    if [[ -z $SSM_DATA_HOME ]]; then
        echo "SSM_DATA_HOME is not set."
        exit 1
    fi

    # Check if the SSM_USER and SSM_DATA_HOME are valid

    if ! id -u "$SSM_USER" &>/dev/null; then
        echo "$SSM_USER: The user SSM_USER does not exist."
        exit 1
    fi

    if [[ ! -e $SSM_DATA_HOME ]]; then
        echo "$SSM_DATA_HOME: The path SSM_DATA_HOME does not exist."
        exit 1
    fi

    declare setup_done_file="$SSM_DATA_HOME/.ssm-setup-done"

    # Run the initial setup if the setup_done_file does not exist
    if [[ ! -e $setup_done_file ]]; then
        # Copy the .ssm-env file to the SSM_DATA_HOME if it does not exist
        /usr/bin/cp -n /shadowsocks-manager/.ssm-env-example "$SSM_DATA_HOME/.ssm-env"

        # Create the required directories
        mkdir -p "$SSM_DATA_HOME/db" "$SSM_DATA_HOME/static"

        # Set the owner of the SSM_DATA_HOME to the SSM_USER
        chown -R "$SSM_USER:$SSM_USER" "$SSM_DATA_HOME"

        # Set the default options
        declare -a default_options=(-c -m -l -u admin -p passw0rd)

        # Run the initial setup, the explicit options may override the default options
        sudo -HE -u "$SSM_USER" ssm-setup "${default_options[@]}" "$@"

        # Create the initial setup signature file
        touch "$setup_done_file" && chown "$SSM_USER:$SSM_USER" "$setup_done_file"
    fi

    # Start the uWSGI and celery services
    service supervisor start

    # Start the nginx in the foreground
    echo "Starting nginx ..."
    nginx -g "daemon off;"
}

main "$@"

exit
