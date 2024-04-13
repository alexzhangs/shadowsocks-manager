#!/usr/bin/env bash

#? Description:
#?   Start the Django server, and the Celery beat and worker.
#?   If you need to run the server under a specific Python environment, make
#?   sure to activate it before to run the server.
#?
#? Usage:
#?   ssm-dev-start.sh [[IP:]PORT]
#?
#? Options:
#?   [[IP:]PORT]
#?
#?   The IP address and the port that the Django server is listening on.
#?   The default IP address is `127.0.0.1`.
#?   The default PORT is `8000`.
#?

# exit on any error
set -e -o pipefail

function main () {
    declare listen=$1

    # don't quote the variable $listen, leave it this way on purpose
    # shellcheck disable=SC2086
    ssm-manage runserver $listen --insecure &
    sleep 1
    ssm-celery -A shadowsocks_manager worker -l info -B &
}

main "$@"

exit
