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
#? Environment:
#?   The following environment variables are used by this script:
#?
#?   - SSM_VERSION
#?
#?     Optional.
#?     Set the version of the shadowsocks-manager Docker image.
#?     The default value is `latest`.
#?
#? Example:
#?   # quick start with default options
#?   $ bash install.sh
#?
#?   # install a specific version of shadowsocks-manager
#?   $ SSM_VERSION=0.1.5 bash install.sh
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

    if [[ $1 == '-h' || $1 == '--help' ]]; then
        usage
        exit 0
    fi

    check-os
    check-docker

    declare SSM_VERSION=${SSM_VERSION:-latest}
    declare ssm_image="alexzhangs/shadowsocks-manager:$SSM_VERSION"
    declare ssm_container_name="ssm-$SSM_VERSION"
    declare ssm_network_name="${ssm_container_name}-network"
    declare memcached_container_name="${ssm_container_name}-memcached"
    declare rabbitmq_container_name="${ssm_container_name}-rabbitmq"

    declare ssm_volume_path=~/"${ssm_container_name}-volume"

    declare -a default_options=(
        -e "SSM_SECRET_KEY=$(guid)"
        -e "SSM_DEBUG=False"
        -e "SSM_MEMCACHED_HOST=$memcached_container_name"
        -e "SSM_RABBITMQ_HOST=$rabbitmq_container_name"
    )

    # create volume path on host
    mkdir -p "$ssm_volume_path"

    echo "Removing the existing container and network if any ..."
    if docker ps -a --format '{{.Names}}' | grep -q "^${memcached_container_name}$"; then
        docker rm -f "$memcached_container_name"
    fi

    if docker ps -a --format '{{.Names}}' | grep -q "^${rabbitmq_container_name}$"; then
        docker rm -f "$rabbitmq_container_name"
    fi

    if docker ps -a --format '{{.Names}}' | grep -q "^${ssm_container_name}$"; then
        docker rm -f "$ssm_container_name"
    fi

    if docker network inspect "$ssm_network_name" &>/dev/null; then
        docker network rm "$ssm_network_name"
    fi

    echo "Creating $ssm_network_name ..."
    docker network create "$ssm_network_name"

    echo "Running $memcached_container_name ..."
    docker run --restart=always -d --network "$ssm_network_name" --name "$memcached_container_name" memcached

    echo "Running $rabbitmq_container_name ..."
    # run rabbitmq, used by celery
    docker run --restart=always -d --network "$ssm_network_name" --name "$rabbitmq_container_name" rabbitmq

    # run shadowsocks-manager
    echo "Running $ssm_container_name ..."
    docker run --restart=always -d -p 80:80 --network "$ssm_network_name" -v "$ssm_volume_path:/var/local/ssm" \
        --name "$ssm_container_name" "$ssm_image" "${default_options[@]}" "$@"
}

main "$@"

exit
