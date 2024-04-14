#!/usr/bin/env bash

#? Description:
#?   Deploy shadowsocks-manager with Docker.
#?   Assume the Docker is installed.
#? 
#? Usage:
#?   install.sh [-e ENVS ...] [-u USERNAME] [-p PASSWORD] [-M EMAIL] [-r PORT_BEGIN] [-R PORT_END] [-h]
#?
#? Options:
#?   [-e ENVS ...]
#?
#?   Set the environment variables in KEY=VALUE format for .env file.
#?   The .env file is used by Django settings.
#?   This option can be used multiple times.
#?
#?   below environment variables are set by default, they can be overridden by this option.
#?
#?   - SSM_SECRET_KEY=$(guid)
#?   - SSM_DEBUG=False
#?   - SSM_MEMCACHED_HOST=ssm-memcached
#?   - SSM_RABBITMQ_HOST=ssm-rabbitmq
#?
#?   [-u USERNAME]
#?   
#?   Username for shadowsocks-manager administrator, default is 'admin'.
#?   
#?   [-p PASSWORD]
#?   
#?   Password for shadowsocks-manager administrator, default is 'passw0rd'.
#?   
#?   [-M EMAIL]
#?   
#?   Email for the shadowsocks-manager administrator.
#?   Also, be used as the sender of the account notification Email.
#?   
#?   [-r PORT_BEGIN]
#?   
#?   Port range allowed for all Shadowsocks nodes.
#?   
#?   [-R PORT_END]
#?   
#?   Port range allowed for all Shadowsocks nodes.
#?
#?   [-h]
#?
#?   This help.
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
    declare -a env_options=("-e" "SSM_SECRET_KEY=$(guid)" "-e" "SSM_DEBUG=False" "-e" "SSM_MEMCACHED_HOST=ssm-memcached" "-e" "SSM_RABBITMQ_HOST=ssm-rabbitmq")
    declare username password email port_begin port_end \
            OPTIND OPTARG opt

    while getopts e:u:p:M:r:R:h opt; do
        case $opt in
            e)
                env_options+=("-e" "$OPTARG")
                ;;
            u)
                username=$OPTARG
                ;;
            p)
                password=$OPTARG
                ;;
            M)
                email=$OPTARG
                ;;
            r)
                port_begin=$OPTARG
                ;;
            R)
                port_end=$OPTARG
                ;;
            *)
                usage
                exit 255
                ;;
        esac
    done

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

    echo "Creating a docker network ..."
    docker network create ssm-network

    echo "Running ssm-memcached ..."
    docker run -d -p 11211:11211 --network ssm-network --name ssm-memcached memcached

    echo "Running ssm-rabbitmq ..."
    # run rabbitmq, used by celery
    docker run -d -p 5672:5672 --network ssm-network --name ssm-rabbitmq rabbitmq

    # run shadowsocks-manager
    echo "Running ssm ..."
    docker run -d -p 80:80 --network ssm-network -v $volume_path:/var/local/ssm --name ssm alexzhangs/shadowsocks-manager \
               "${env_options[@]}" -u "$username" -p "$password" -M "$email" -r "$port_begin" -R "$port_end"
}

main "$@"

exit
