#!/bin/bash

#? Description:
#?   Install the project files of shadowsocks-manager.
#?   Run this script under root on Linux.
#?
#?   The following actions are taken:
#?     * create user
#?     * create virtualenv
#?     * copy project files
#?     * copy nginx and supervisor files if the services present
#?     * create django static dir
#?
#? Usage:
#?   install.sh
#?
declare WORK_DIR=$(cd "$(dirname "$0")"; pwd)
source "$WORK_DIR/common.sh"

function create-user () {
    printf "Creating user $SSM_USER...\n"
    if id $SSM_USER >/dev/null 2>&1; then
        userdel -r $SSM_USER
    fi
    useradd -m $SSM_USER
}

function create-virtualenv () {
    # set VENV_* environment variables
    set-virtualenv-vars

    printf "Creating virtualenv $SSM_USER in $VENV_HOME ...\n"
    (cd "$VENV_HOME" && virtualenv "$SSM_USER" && chown -R $SSM_USER:$SSM_USER "$SSM_USER")
}

function install-project-files () {
    printf "Copying project files to $INSTALL_DIR...\n"
    cp -a "$WORK_DIR" "$INSTALL_DIR"
    chown -R $SSM_USER:$SSM_USER "$INSTALL_DIR"
}

function install-nginx-conf () {
    # if nginx is available
    if [[ -d /etc/nginx ]]; then
        printf "Copying nginx conf files...\n"
        cp -a "$WORK_DIR"/nginx/* /etc/nginx/
    fi
}

function install-supervisor-conf () {
    # if supervisor is available
    if type -t supervisord >/dev/null; then
        if [[ ! -e /etc/default ]]; then
            mkdir -p /etc/default
        fi
        printf "Copying supervisor profile...\n"
        cp -av "$WORK_DIR"/supervisor/profile/* /etc/default/

        if [[ ! -e /etc/ssupervisorupervisor/conf.d ]]; then
            mkdir -p /etc/supervisor/conf.d
        fi
        printf "Copying supervisor vendors...\n"
        cp -av "$WORK_DIR"/supervisor/vendors/*.ini /etc/supervisor/conf.d/

        # don't restart supervisord or reload the vendors, the app server is
        # not ready yet.
    fi
}

function create-django-static-dir () {
    printf "Creating Django static dir: $DJANGO_STATIC_DIR ...\n"
    mkdir -p "$DJANGO_STATIC_DIR"
    chown $SSM_USER:$SSM_USER "$DJANGO_STATIC_DIR"
}

function main () {
    create-user
    create-virtualenv
    install-project-files
    install-nginx-conf
    install-supervisor-conf
    create-django-static-dir
}

main "$@"

exit
