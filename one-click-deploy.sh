#!/bin/bash

#? Description:
#?   Deploy shadowsocks-manager with one single command.
#?   Run this script under root on Linux.
#? 
#? Usage:
#?   one-click-deploy.sh [-n DOMAIN] [-u USERNAME] [-p PASSWORD] [-e EMAIL] [-t TIMEZONE] [-o PORT_BEGIN] [-O PORT_END] [-h]
#?
#? Options:
#?   [-n DOMAIN]
#?   
#?   Domain name resolved to the shadowsocks-manager web application.
#?   
#?   [-u USERNAME]
#?   
#?   Username for shadowsocks-manager administrator, default is 'admin'.
#?   
#?   [-p PASSWORD]
#?   
#?   Password for shadowsocks-manager administrator, default is 'passw0rd'.
#?   
#?   [-e EMAIL]
#?   
#?   Email for the shadowsocks-manager administrator.
#?   Also, be used as the sender of the account notification Email.
#?   
#?   [-t TIMEZONE]
#?   
#?   Set Django's timezone, default is 'UTC'.
#?   Statistics period also senses this setting. Note that AWS billing is based on UTC.
#?   
#?   [-r PORT_BEGIN]
#?   
#?   Port range allowed for all Shadowsocks nodes.
#?   
#?   [-R PORT_END]
#?   
#?   Port range allowed for all Shadowsocks nodes.
#?
#?   [-h]
#?
#?   This help.
#?
declare WORK_DIR=$(cd "$(dirname "$0")"; pwd)
source "$WORK_DIR/common.sh"

function main () {
    declare DOMAIN USERNAME PASSWORD EMAIL TIMEZONE PORT_BEGIN PORT_END \
            OPTIND OPTARG opt

    while getopts n:u:p:e:t:r:Rh opt; do
        case $opt in
            n)
                DOMAIN=$OPTARG
                ;;
            u)
                USERNAME=$OPTARG
                ;;
            p)
                PASSWORD=$OPTARG
                ;;
            e)
                EMAIL=$OPTARG
                ;;
            t)
                TIMEZONE=$OPTARG
                ;;
            r)
                PORT_BEGIN=$OPTARG
                ;;
            R)
                PORT_END=$OPTARG
                ;;
            *)
                usage
                exit 255
                ;;
        esac
    done

    # required, install rabbitmq-server, memcached, pip
    bash "$WORK_DIR/install-dependency.sh"

    # optional but recommended, install gcc, nginx, supervisor
    bash "$WORK_DIR/install-extra.sh"

    # required, install shadowsocks-manager itself
    bash "$WORK_DIR/install.sh"

    # required, setup shadowsocks-manager
    sudo -u "$SSM_USER" bash "$INSTALL_DIR/setup.sh" "$@"

    supervisorctl reload
    service nginx reload
}

main "$@"

exit
