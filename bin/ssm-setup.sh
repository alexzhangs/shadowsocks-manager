#!/usr/bin/env bash

#? Description:
#?   Setup shadowsocks-manager in your Python environment.
#?   If you need to run the setup under a specific Python environment, make
#?   sure to activate it before to run the setup.
#?
#? Usage:
#?   ssm-setup.sh [-e ENV ...]
#?                [-c] [-m] [-l] [-u USERNAME -p PASSWORD [-M EMAIL]] [-r PORT_BEGIN] [-R PORT_END] [-h]
#?
#? Options:
#?   [-e ENV ...]
#?
#?   Set the environment variables in KEY=VALUE format for .env file.
#?   The .env file is used by Django settings.
#?   This option can be used multiple times.
#?
#?   The valid KEYs are:
#?
#?   - SSM_SECRET_KEY
#?
#?     Set Django's SECRET_KEY.
#?     The default value is hardcoded in the .env file and Django's settings.
#?     Do not use the default value in production environment.
#?     Below command will generate a random SECRET_KEY:
#?     ```sh
#?     $ od -vN 25 -An -tx1 /dev/urandom | tr -d ' \n'
#?     ```
#?
#?   - SSM_DEBUG
#?
#?     Set Django's DEBUG.
#?     The value can be 'True' or 'False'.
#?     The default value depends on the .env file and Django's settings.
#?     Do not use value SSM_DEBUG=True in production environment.
#?
#?   - SSM_TIME_ZONE
#?
#?     Set Django's TIME_ZONE.
#?     The value can be any valid timezone name.
#?     The default value depends on the .env file and Django's settings.
#?
#?   - SSM_DATA_HOME
#?
#?     Set the base directory for the Django database and static files.
#?     The default value depends on the .env file and Django's settings.
#?
#?   - SSM_MEMCACHED_HOST, SSM_MEMCACHED_PORT
#?
#?     Set the Memcached server's host and port which are used by Django cache.
#?     The default value depends on the .env file and Django's settings.
#? 
#?   - SSM_RABBITMQ_HOST, SSM_RABBITMQ_PORT
#?
#?     Set the RabbitMQ server's host and port which are used by Celery.
#?     The default value depends on the .env file and Django's settings.
#?
#?   However, this script will not check the validity of the KEYs and VALUEs.
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
#?   No default value.
#?   This is necessary for the first time setup.
#?
#?   [-p PASSWORD]
#?
#?   Password for shadowsocks-manager administrator'.
#?   No default value.
#?   This is necessary for the first time setup.
#?
#?   [-M EMAIL]
#?
#?   Email for the shadowsocks-manager administrator.
#?   Also, be used as the sender of the account notification Email.
#?   No default value.
#?
#?   [-r PORT_BEGIN]
#?
#?   The beginning port number for Shadowsocks nodes.
#?   The default value depends on the Django fixture data.
#?
#?   [-R PORT_END]
#?
#?   The ending port number for Shadowsocks nodes.
#?   The default value depends on the Django fixture data.
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
#?   $ ssm-setup -e SSM_SECRET_KEY=yourkey -e SSM_DEBUG=False
#?
#?   # First time setup in production environment:
#?   $ ssm-setup -e SSM_SECRET_KEY=yourkey -e SSM_DEBUG=False -c -m -l -u admin -p yourpassword -M admin@yourdomain.com
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

function main () {
    declare -a envs
    declare collect_flag migrate_flag loaddata_flag username password email port_begin port_end \
            OPTIND OPTARG opt

    while getopts e:cmlu:p:M:r:R:h opt; do
        case $opt in
            e)
                envs+=("$OPTARG")
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
            M)
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

    if [[ -n ${envs[*]} ]]; then
        ssm-dotenv -w "${envs[@]}"
    fi

    if [[ -n $collect_flag ]]; then
        ssm-manage collectstatic --no-input -c
    fi

    if [[ -n $migrate_flag ]]; then
        ssm-manage makemigrations
        ssm-manage migrate
    fi

    if [[ -n $loaddata_flag ]]; then
        ssm-manage loaddata fixtures/auth.group.json \
               fixtures/sites.site.json \
               fixtures/django_celery_beat.crontabschedule.json \
               fixtures/django_celery_beat.intervalschedule.json \
               fixtures/django_celery_beat.periodictask.json \
               config.json \
               template.json \
               nameserver.json
    fi

    if [[ -n $username && -n $password ]]; then
        ssm-createsuperuser --username "$username" --password "$password" --email "$email"
    fi

    if [[ -n $port_begin ]]; then
        ssm-manage shadowsocks_config --port-begin "$port_begin"
    fi

    if [[ -n $port_end ]]; then
        ssm-manage shadowsocks_config --port-end "$port_end"
    fi
}

main "$@"

exit
