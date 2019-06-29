#!/bin/bash

# Exit on any error
set -o pipefail -e

usage () {
    printf "Usage: ${0##*/} [-n DOMAIN] [-a IP] [- USERNAME] [-p PASSWORD] [-e EMAIL] [-t TIMEZONE]\n"
    printf "Run this script under root on Linux.\n"
    printf "OPTIONS\n"
    printf "\t[-n DOMAIN]\n\n"
    printf "\tDomain name resolved to shadowsocks-manager web application.\n\n"
    printf "\t[-a IP]\n\n"
    printf "\tIP address bound to shadowsocks-manager web application, default is 127.0.0.1.\n\n"
    printf "\t[-u USERNAME]\n\n"
    printf "\tUsername for shadowsocks-manager administrator, default is 'admin'.\n\n"
    printf "\t[-p PASSWORD]\n\n"
    printf "\tPassword for shadowsocks-manager administrator, default is 'passw0rd'.\n\n"
    printf "\t[-e EMAIL]\n\n"
    printf "\tEmail for shadowsocks-manager administrator.\n\n"
    printf "\t[-t TIMEZONE]\n\n"
    printf "\tDefault is 'UTC'.\n\n"
    printf "\t[-h]\n\n"
    printf "\tThis help.\n\n"
    exit 255
}

while getopts n:a:u:p:e:t:h opt; do
    case $opt in
        n)
            DOMAIN=$OPTARG
            ;;
        a)
            IP=$OPTARG
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
        *|h)
            usage
            ;;
    esac
done

[[ -z $IP ]] && IP=127.0.0.1
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
    userdel -m $RUN_AS
fi
useradd $RUN_AS

printf "Copying project files to $INSTALL_DIR...\n"
su - $RUN_AS -c "cp -a $WORK_DIR $INSTALL_DIR"

printf "Changing to install directory...\n"
cd "$INSTALL_DIR"

printf "Installing python dependencies...\n"
pip install -r requirements.txt

printf "Modifying nginx conf files...\n"
sed -i "s/{DOMAIN}/${DOMAIN}/" nginx/conf.d/shadowsocks-manager.conf

printf "Copying nginx conf files...\n"
cp -a nginx/* /etc/nginx/

printf "Copying supervisor program conf files...\n"
cp -a supervisor/* /etc/supervisor/conf.d/

STATIC_DIR="/var/local/www/$DOMAIN/static/"
printf "Creating static dir: $STATIC_DIR...\n"
mkdir -p "$STATIC_DIR"

function guid () {
    od -vN "$(($1 / 2))" -An -tx1 /dev/urandom | tr -d ' \n'
}

printf "Modifying Django settings...\n"
secret_key=$(guid 50)
setting_file="$INSTALL_DIR/shadowsocks_manager/settings.py"
sed -e "s/DEBUG = True/DEBUG = False/" \
    -e "s/ALLOWED_HOSTS = .*/ALLOWED_HOSTS = ['$IP', '$DOMAIN']/" \
    -e "s|STATIC_ROOT = .*|STATIC_ROOT = '$STATIC_DIR'|" \
    -e "s/SECRET_KEY = .*/SECRET_KEY = '$secret_key'/" \
    -e "s/TIME_ZONE = .*/TIME_ZONE = '$TIMEZONE'/" \
    -i "$setting_file"

printf "Changing to Django directory...\n"
cd "$INSTALL_DIR/shadowsocks_manager"

printf "Load Django fixtures...\n"
python manage.py makemigrations
python manage.py migrate
python manage.py loaddata auth.group.json \
       django_celery_beat.crontabschedule.json \
       django_celery_beat.intervalschedule.json \
       django_celery_beat.periodictask.json \
       config.json \
       template.json

printf "Creating super user...\n"
echo "from django.contrib.auth.models import User; User.objects.filter(username='$USERNAME').delete(); User.objects.create_superuser('$USERNAME', '$EMAIL', '$PASSWORD')" \
    | python manage.py shell

printf "Collecting static files...\n"
python manage.py collectstatic --no-input -c

exit
