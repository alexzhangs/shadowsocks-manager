#!/usr/bin/env bash

#? Description:
#?   Setup shadowsocks-manager in your Python environment.
#?   If you need to run the setup under a specific Python environment, make
#?   sure to activate it before to run the setup.
#?
#? Usage:
#?   ssm-setup.sh [-k SECRET_KEY | -K] [-d | -D] [-t TIMEZONE] [-c] [-m] [-l] [-u USERNAME -p PASSWORD [-e EMAIL]] [-r PORT_BEGIN] [-R PORT_END] [-h]
#?
#? Options:
#?   [-k SECRET_KEY]
#?
#?   Set Django's SECRET_KEY.
#?   Please use either -k or -K to update the default SECRET_KEY in production environment.
#?
#?   [-K]
#?
#?   Set Django's SECRET_KEY to a random value. You can fetch this value afterwords from the .env file.
#?
#?   [-d]
#?
#?   Set Django's DEBUG to True.
#?   Do not use this option in production environment.
#?
#?   [-D]
#?
#?   Set Django's DEBUG to False, this is django's default setting.
#?   Please use this option in production environment.
#?
#?   [-t TIMEZONE]
#?
#?   Set Django's TIMEZONE, default is 'UTC'.
#?   Statistic period also senses this setting. Note that AWS billing is based on UTC.
#?
#?   [-c]
#?
#?   Collect Django static files.
#?   This is necessary for the first time setup.
#?
#?   [-m]
#?
#?   Migrate Django database.
#?   This is necessary for the first time setup.
#?
#?   [-l]
#?
#?   Load Django fixtures.
#?   This is necessary for the first time setup.
#?
#?   [-u USERNAME]
#?
#?   Username for shadowsocks-manager administrator.
#?   This is necessary for the first time setup.
#?
#?   [-p PASSWORD]
#?
#?   Password for shadowsocks-manager administrator'.
#?   This is necessary for the first time setup.
#?
#?   [-e EMAIL]
#?
#?   Email for the shadowsocks-manager administrator.
#?   Also, be used as the sender of the account notification Email.
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
#? Example:
#?   # First time setup in development environment:
#?   $ ssm-setup -c -m -l -u admin -p yourpassword
#?
#?   # Update a development environment to be production ready:
#?   $ ssm-setup -K -D
#?
#?   # First time setup in production environment:
#?   $ ssm-setup -K -D -c -m -l -u admin -p yourpassword -e admin@example.com
#?

# exit on any error
set -e -o pipefail

function usage () {
    awk '/^#\?/ {sub("^[ ]*#\\?[ ]?", ""); print}' "$0" \
        | awk '{gsub(/^[^ ]+.*/, "\033[1m&\033[0m"); print}'
}

function check-os () {
    if [[ $(uname) != 'Linux' && $(uname) != 'Darwin' ]]; then
        printf "fatal: this script support Linux and MacOS only.\n" >&2
        return 255
    fi
}

function guid () {
    od -vN "$(($1 / 2))" -An -tx1 /dev/urandom | tr -d ' \n'
}

function main () {
    declare secret_key debug_flag timezone collect_flag migrate_flag loaddata_flag username password email port_begin port_end \
            OPTIND OPTARG opt

    while getopts k:KdDt:cmlu:p:e:r:R:h opt; do
        case $opt in
            k)
                secret_key=$OPTARG
                ;;
            K)
                secret_key=$(guid 50)
                ;;
            d)
                debug_flag=True
                ;;
            D)
                debug_flag=False
                ;;
            t)
                timezone=$OPTARG
                ;;
            c)
                collect_flag=1
                ;;
            m)
                migrate_flag=1
                ;;
            l)
                loaddata_flag=1
                ;;
            u)
                username=$OPTARG
                ;;
            p)
                password=$OPTARG
                ;;
            e)
                email=$OPTARG
                ;;
            r)
                port_begin=$OPTARG
                ;;
            R)
                port_end=$OPTARG
                ;;
            *)
                usage
                exit 255
                ;;
        esac
    done

    check-os

    if [[ $# -eq 0 ]]; then
        usage
        exit 255
    fi

    if [[ -n $secret_key ]]; then
        ssm-dotenv -w "SSM_SECRET_KEY=$secret_key"
    fi

    if [[ -n $debug_flag ]]; then
        ssm-dotenv -w "SSM_DEBUG=$debug_flag"
    fi

    if [[ -n $timezone ]]; then
        ssm-dotenv -w "SSM_TIME_ZONE=$timezone"
    fi

    if [[ -n $collect_flag ]]; then
        ssm collectstatic --no-input -c
    fi

    if [[ -n $migrate_flag ]]; then
        ssm makemigrations
        ssm migrate
    fi

    if [[ -n $loaddata_flag ]]; then
        ssm loaddata fixtures/auth.group.json \
               fixtures/sites.site.json \
               fixtures/django_celery_beat.crontabschedule.json \
               fixtures/django_celery_beat.intervalschedule.json \
               fixtures/django_celery_beat.periodictask.json \
               config.json \
               template.json \
               nameserver.json
    fi

    if [[ -n $username && -n $password ]]; then
        ssm-superuser --username "$username" --password "$password" --email "$email"
    fi

    if [[ -n $port_begin ]]; then
        ssm shadowsocks_config --port-begin "$port_begin"
    fi

    if [[ -n $port_end ]]; then
        ssm shadowsocks_config --port-end "$port_end"
    fi
}

main "$@"

exit
