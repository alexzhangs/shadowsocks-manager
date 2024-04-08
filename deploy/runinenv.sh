#!/bin/bash

#? Description:
#?   Run commands inside a virtualenv.
#?   https://gist.github.com/parente/826961#file-runinenv-sh
#?
#? Usage:
#?   runinenv.sh VIRTUALENV_PATH CMDS [OPTIONS]
#?
function usage () {
    awk '/^#\?/ {sub("^[ ]*#\\?[ ]?", ""); print}' "$0" \
        | awk '{gsub(/^[^ ]+.*/, "\033[1m&\033[0m"); print}'
}

declare VENV=$1
shift

if [[ -z $VENV ]]; then
    usage
    exit 255
fi

. "$VENV/bin/activate"
echo "Executing $@ in $VENV"
exec "$@"
