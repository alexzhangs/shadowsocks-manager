#!/bin/bash

#? Description:
#?   Install the project file of shadowsocks-manager.
#?   Run this script under root on Linux.
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
    if [[ -d /etc/supervisor/conf.d ]]; then
        printf "Copying supervisor program conf files...\n"
        cp -a "$WORK_DIR"/supervisor/* /etc/supervisor/conf.d/
    fi
}

function create-django-static-dir () {
    printf "Creating Django static dir: $DJANGO_STATIC_DIR\n"
    mkdir -p "$DJANGO_STATIC_DIR"
    chown $SSM_USER:$SSM_USER "$DJANGO_STATIC_DIR"
}

function main () {
    create-user
    install-project-files
    install-nginx-conf
    install-supervisor-conf
    create-django-static-dir
}

main "$@"

exit
