#!/bin/bash

#? Description:
#?   Start the Django testing server, and the Celery beat and worker.
#?   If you need to run the setup under a specific Python environment, make
#?   sure to activate it before to run the setup.
#?
#? Usage:
#?   start-testserver.sh [[IP:]PORT]
#?
#? Options:
#?   [[IP:]PORT]
#?
#?   The IP address and the port that the Django server is listening on.
#?   The default IP address is `127.0.0.1`.
#?   The default PORT is `8000`.
#?
declare WORK_DIR=$(cd "$(dirname "$0")"; pwd)
source "$WORK_DIR/common.sh"

function main () {
    declare listen=$1

    printf "Changing to Django directory...\n"
    cd "$WORK_DIR/shadowsocks_manager"

    python manage.py runserver $listen --insecure &
    celery -A shadowsocks_manager worker -l info -B &
}

main "$@"

exit
