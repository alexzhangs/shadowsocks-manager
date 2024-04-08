#!/usr/bin/env bash

#? Description:
#?   Stop the Django testing server, and the Celery beat and worker.
#?
#? Usage:
#?   ssm-stop-testserver.sh
#?

function main () {
    # Kill the Celery worker and beat processes
    pkill -f "celery -A shadowsocks_manager.shadowsocks_manager worker -l info -B"

    # Kill the Django runserver process
    pkill -f "ssm runserver"
}

main "$@"

exit
