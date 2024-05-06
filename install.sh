#!/usr/bin/env bash

#? Description:
#?   Deploy shadowsocks-manager with Docker.
#?   Assume the Docker is installed.
#? 
#? Usage:
#?   install.sh [SSM_SETUP_OPTIONS]
#?
#? Options:
#?   [SSM_SETUP_OPTIONS]
#?
#?   Options are the same as the ssm-setup script.
#?   If any option is provided, the options will pass along with the default options to the `docker run` command.
#?   The default options are:
#?
#?     -e SSM_SECRET_KEY=$(guid)
#?     -e SSM_DEBUG=False
#?     -e SSM_MEMCACHED_HOST=ssm-memcached
#?     -e SSM_RABBITMQ_HOST=ssm-rabbitmq
#?
#? Example:
#?   # quick start with default options
#?   $ bash install.sh
#?

# exit on any error
set -e -o pipefail

function usage () {
    awk '/^#\?/ {sub("^[ ]*#\\?[ ]?", ""); print}' "$0" \
        | awk '{gsub(/^[^ ]+.*/, "\033[1m&\033[0m"); print}'
}

function check-os () {
    if [[ $(uname) != 'Linux' && $(uname) != 'Darwin' ]]; then
        printf "fatal: this script support Linux and MacOS only.\n" >&2
        return 255
    fi
}

function check-docker () {
    if ! command -v docker &>/dev/null; then
        printf "fatal: docker is not installed.\n" >&2
        return 255
    fi
}

function guid () {
    # generate a random guid
    od -vN 25 -An -tx1 /dev/urandom | tr -d ' \n'
}

function main () {
    declare -a default_options=(
        -e "SSM_SECRET_KEY=$(guid)"
        -e "SSM_DEBUG=False"
        -e "SSM_MEMCACHED_HOST=ssm-memcached"
        -e "SSM_RABBITMQ_HOST=ssm-rabbitmq")

    check-os
    check-docker

    declare volume_path=~/ssm-volume

    # create volume path on host
    mkdir -p "$volume_path"

    echo "Removing the existing container and network if any ..."
    if docker ps -a --format '{{.Names}}' | grep -q '^ssm-memcached$'; then
        docker rm -f ssm-memcached
    fi

    if docker ps -a --format '{{.Names}}' | grep -q '^ssm-rabbitmq$'; then
        docker rm -f ssm-rabbitmq
    fi

    if docker ps -a --format '{{.Names}}' | grep -q '^ssm$'; then
        docker rm -f ssm
    fi

    if docker network inspect ssm-network &>/dev/null; then
        docker network rm ssm-network
    fi

    echo "Creating ssm-network ..."
    docker network create ssm-network

    echo "Running ssm-memcached ..."
    docker run -d --network ssm-network --name ssm-memcached memcached

    echo "Running ssm-rabbitmq ..."
    # run rabbitmq, used by celery
    docker run -d --network ssm-network --name ssm-rabbitmq rabbitmq

    # run shadowsocks-manager
    echo "Running ssm ..."
    docker run -d -p 80:80 --network ssm-network -v $volume_path:/var/local/ssm \
        --name ssm alexzhangs/shadowsocks-manager "${default_options[@]}" "$@"
}

main "$@"

exit
