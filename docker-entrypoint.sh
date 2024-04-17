#!/usr/bin/env bash

#? Description:
#?   This script is the entrypoint for the shadowsocks-manager container.
#?   It will:
#?   - Setup the shadowsocks-manager
#?   - Start the uWSGI and celery services
#?   - Start the nginx service
#?
#?   This script should be called by user root.
#?
#? Usage:
#?   docker-entrypoint.sh [OPTIONS]
#?
#? Options:
#?   [OPTIONS]
#?
#?   Options are the same as the ssm-setup script.
#?   If any option is provided, the ssm-setup will be executed with the provided options.
#?
#? Environment:
#?   The following environment variables are used by this script:
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
#?     Set the base directory for the Django database and static files.
#?     The path should exist in the container and should be writable by the SSM_USER.
#?     It should be mounted as a volume in the container while running the docker image.
#?
#?     Django collectstatic will be executed if the path `$SSM_DATA_HOME/static` is empty.
#?     Django migrate, loaddata and createsuperuser will be executed if the path `$SSM_DATA_HOME/db` is empty.
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

    # Create the required directories
    mkdir -p "$SSM_DATA_HOME/db" "$SSM_DATA_HOME/static"

    # Set the owner of the SSM_DATA_HOME to the SSM_USER
    chown -R "$SSM_USER:$SSM_USER" "$SSM_DATA_HOME"

    # Setup the shadowsocks-manager with default options and the provided options
    sudo -H -u "$SSM_USER" ssm-setup -e SSM_DATA_HOME="$SSM_DATA_HOME" "$@"

    # Check if the static files are collected
    if [[ -z "$(ls -A "$SSM_DATA_HOME"/static)" ]]; then
        # Collect the static files
        sudo -H -u "$SSM_USER" ssm-setup -c
    fi

    # Check if the database is migrated
    if [[ -z "$(ls -A "$SSM_DATA_HOME"/db)" ]]; then
        # Migrate the database, loaddata and createsuperuser
        sudo -H -u "$SSM_USER" ssm-setup -m -l -u admin -p passw0rd
    fi

    # Start the uWSGI and celery services
    service supervisor start

    # Start the nginx in the foreground
    echo "Starting nginx ..."
    nginx -g "daemon off;"
}

main "$@"

exit
