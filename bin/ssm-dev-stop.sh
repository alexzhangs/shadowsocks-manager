#!/usr/bin/env bash

#? Description:
#?   Stop the Django server, and the Celery beat and worker.
#?
#? Usage:
#?   ssm-dev-stop.sh
#?

function main () {
    # Kill the Celery processes
    pkill -f "celery -A shadowsocks_manager"

    # Kill the Django runserver process
    pkill -f "python manage.py runserver"
}

main "$@"

exit
