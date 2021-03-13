#!/bin/bash

#? Description:
#?   Setup shadowsocks-manager in your Python environment.
#?   If you need to run the setup under a specific Python environment, make
#?   sure to activate it before to run the setup.
#?   Run this script under root on Linux.
#?
#? Usage:
#?   setup.sh [-n DOMAIN] [-u USERNAME] [-p PASSWORD] [-e EMAIL] [-t TIMEZONE] [-o PORT_BEGIN] [-O PORT_END] [-h]
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
#?   Statistic period also senses this setting. Note that AWS billing is based on UTC.
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

function install-python-dependency () {
    printf "Installing python dependencies...\n"
    pip install --ignore-installed -r "$WORK_DIR/requirements.txt"
}

function setup-django () {

    function guid () {
        od -vN "$(($1 / 2))" -An -tx1 /dev/urandom | tr -d ' \n'
    }

    printf "Modifying Django settings...\n"
    sed -e "s/DEBUG = True/DEBUG = False/" \
        -e "s/DOMAIN = .*/DOMAIN = '$DOMAIN'/" \
        -e "s/SECRET_KEY = .*/SECRET_KEY = '$(guid 50)'/" \
        -e "s/TIME_ZONE = .*/TIME_ZONE = '$TIMEZONE'/" \
        -e "s|STATIC_ROOT = .*|STATIC_ROOT = '$DJANGO_STATIC_DIR'|" \
        -i "$WORK_DIR/shadowsocks_manager/shadowsocks_manager/settings.py"
}

function migrate-django () {
    printf "Migrating Django...\n"
    python manage.py makemigrations
    python manage.py migrate
}

function load-django-data () {
    printf "Loading Django fixtures...\n"
    python manage.py loaddata auth.group.json \
           django_celery_beat.crontabschedule.json \
           django_celery_beat.intervalschedule.json \
           django_celery_beat.periodictask.json \
           config.json \
           template.json \
           nameserver.json
}

function create-django-admin () {
    printf "Creating super user...\n"
    echo "from django.contrib.auth.models import User;
User.objects.filter(username='$USERNAME').delete();
User.objects.create_superuser('$USERNAME', '$EMAIL', '$PASSWORD')" \
        | python manage.py shell
}

function setup-app-config () {
    printf "Setting Shadowsocks port range...\n"
    echo "from shadowsocks.models import Config;
config = Config.load();
config.port_begin = '$PORT_BEGIN' or config.port_begin;
config.port_end = '$PORT_END' or config.port_end;
config.save()" \
        | python manage.py shell
}

function collect-django-static () {
    printf "Collecting static files...\n"
    python manage.py collectstatic --no-input -c
}

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

    [[ -z $USERNAME ]] && USERNAME=admin
    [[ -z $PASSWORD ]] && PASSWORD=passw0rd
    [[ -z $TIMEZONE ]] && TIMEZONE=UTC

    printf "Changing to Django directory...\n"
    cd "$WORK_DIR/shadowsocks_manager"

    install-python-dependency
    setup-django
    migrate-django
    load-django-data
    create-django-admin
    setup-app-config
    collect-django-static
}

main "$@"

exit
