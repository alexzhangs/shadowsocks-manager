#!/usr/bin/env bash

#? Description:
#?   Start the Django server, and the Celery beat and worker.
#?   If you need to run the server under a specific Python environment, make
#?   sure to activate it before to run the server.
#?
#? Usage:
#?   ssm-dev-start.sh [OPTIONS]
#?
#? Options:
#?   [OPTIONS]
#?
#?   The options are transparenctly passing to django runserver.
#?   The default options are `--insecure`.
#?
#? Environment:
#?   The following environment variables are optional:
#?
#?   - SSM_DEV_CELERY_LOG_LEVEL
#?
#?     The log level for Celery worker and beat.
#?     Default is `info`.
#?

# exit on any error
set -e -o pipefail

trap 'ssm-dev-stop' EXIT

function main () {
    ssm-celery -A shadowsocks_manager worker -D -l "${SSM_DEV_CELERY_LOG_LEVEL:info}" -B
    ssm-manage runserver "${@:---insecure}"
}

main "$@"

exit
