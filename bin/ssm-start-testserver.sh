#!/usr/bin/env bash

#? Description:
#?   Start the Django testing server, and the Celery beat and worker.
#?   If you need to run the setup under a specific Python environment, make
#?   sure to activate it before to run the setup.
#?
#? Usage:
#?   ssm-start-testserver.sh [[IP:]PORT]
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
    ssm runserver $listen --insecure &
    sleep 1
    celery -A shadowsocks_manager.shadowsocks_manager worker -l info -B &
}

main "$@"

exit
