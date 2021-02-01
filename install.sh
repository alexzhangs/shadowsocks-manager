#!/bin/bash

# Exit on any error
set -o pipefail -e

usage () {
    printf "Usage: ${0##*/} [-n DOMAIN] [-u USERNAME] [-p PASSWORD] [-e EMAIL] [-t TIMEZONE] [-o PORT_BEGIN] [-O PORT_END]\n"
    printf "Run this script under root on Linux.\n"
    printf "OPTIONS\n"
    printf "\t[-n DOMAIN]\n\n"
    printf "\tDomain name resolved to shadowsocks-manager web application.\n\n"
    printf "\t[-u USERNAME]\n\n"
    printf "\tUsername for shadowsocks-manager administrator, default is 'admin'.\n\n"
    printf "\t[-p PASSWORD]\n\n"
    printf "\tPassword for shadowsocks-manager administrator, default is 'passw0rd'.\n\n"
    printf "\t[-e EMAIL]\n\n"
    printf "\tEmail for shadowsocks-manager administrator.\n\n"
    printf "\t[-t TIMEZONE]\n\n"
    printf "\tDefault is 'UTC'.\n\n"
    printf "\t[-r PORT_BEGIN]\n\n"
    printf "\tPort range allowed for all Shadowsocks nodes.\n\n"
    printf "\t[-R PORT_END]\n\n"
    printf "\tPort range allowed for all Shadowsocks nodes.\n\n"
    printf "\t[-h]\n\n"
    printf "\tThis help.\n\n"
    exit 255
}

while getopts n:u:p:e:t:r:R:h opt; do
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
        *|h)
            usage
            ;;
    esac
done

[[ -z $USERNAME ]] && USERNAME=admin
[[ -z $PASSWORD ]] && PASSWORD=passw0rd
[[ -z $TIMEZONE ]] && TIMEZONE=UTC

WORK_DIR=$(cd "$(dirname "$0")"; pwd)

if [[ $(uname) != 'Linux' ]]; then
    printf "Error: this script support Linux only.\n" >&2
    exit 9
fi

RUN_AS=ssm
INSTALL_DIR=/home/$RUN_AS/shadowsocks-manager

printf "Creating user $RUN_AS...\n"
if id $RUN_AS >/dev/null 2>&1; then
    userdel -r $RUN_AS
fi
useradd $RUN_AS

printf "Copying project files to $INSTALL_DIR...\n"
su $RUN_AS -c "cp -a $WORK_DIR $INSTALL_DIR"

printf "Changing to install directory...\n"
cd "$INSTALL_DIR"

printf "Installing python dependencies...\n"
pip install --ignore-installed -r requirements.txt

# if nginx is available
if [[ -d /etc/nginx ]]; then
    printf "Copying nginx conf files...\n"
    cp -a nginx/* /etc/nginx/
fi

# if supervisor is available
if [[ -d /etc/supervisor/conf.d ]]; then
    printf "Copying supervisor program conf files...\n"
    cp -a supervisor/* /etc/supervisor/conf.d/
fi

function guid () {
    od -vN "$(($1 / 2))" -An -tx1 /dev/urandom | tr -d ' \n'
}

printf "Modifying Django settings...\n"
STATIC_DIR="/var/local/www/ssm/static/"
SECRET_KEY=$(guid 50)
SETTING_FILE="$INSTALL_DIR/shadowsocks_manager/shadowsocks_manager/settings.py"
sed -e "s/DEBUG = True/DEBUG = False/" \
    -e "s/DOMAIN = .*/DOMAIN = '$DOMAIN'/" \
    -e "s|STATIC_ROOT = .*|STATIC_ROOT = '$STATIC_DIR'|" \
    -e "s/SECRET_KEY = .*/SECRET_KEY = '$SECRET_KEY'/" \
    -e "s/TIME_ZONE = .*/TIME_ZONE = '$TIMEZONE'/" \
    -i "$SETTING_FILE"

printf "Changing to Django directory...\n"
cd "$INSTALL_DIR/shadowsocks_manager"

printf "Migrating Django...\n"
su $RUN_AS -c "python manage.py makemigrations"
su $RUN_AS -c "python manage.py migrate"

printf "Loading Django fixtures...\n"
su $RUN_AS -c "python manage.py loaddata auth.group.json \
       django_celery_beat.crontabschedule.json \
       django_celery_beat.intervalschedule.json \
       django_celery_beat.periodictask.json \
       config.json \
       template.json \
       nameserver.json"

printf "Creating super user...\n"
echo "from django.contrib.auth.models import User;
User.objects.filter(username='$USERNAME').delete();
User.objects.create_superuser('$USERNAME', '$EMAIL', '$PASSWORD')" \
    | su $RUN_AS -c "python manage.py shell"

printf "Setting Shadowsocks port range...\n"
echo "from shadowsocks.models import Config;
config = Config.load();
config.port_begin = '$PORT_BEGIN' or config.port_begin;
config.port_end = '$PORT_END' or config.port_end;
config.save()" \
    | su $RUN_AS -c "python manage.py shell"

printf "Creating static dir: $STATIC_DIR...\n"
mkdir -p "$STATIC_DIR"
chown $RUN_AS:$RUN_AS "$STATIC_DIR"

printf "Collecting static files...\n"
su $RUN_AS -c "python manage.py collectstatic --no-input -c"

exit

