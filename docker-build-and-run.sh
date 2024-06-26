#!/usr/bin/env bash

#? Description:
#?   Build the Docker images and run the containers for testing.
#?
#?   Without any option, it will build the images in sequence and run the containers in the foreground.
#?   In the foreground mode:
#?   - The output of the containers will be displayed in the terminal.
#?   - The ports 80 and 443 will be published to the host for each container.
#?   - In order to proceed to run the next container, you need to stop or remove the current container manually.
#?
#? Usage:
#?   docker-build-and-run.sh [-p] [-P] [-m] [-d] [DISTRIBUTION ..] [-- RUN_CMD_OPTIONS ..]
#?   docker-build-and-run.sh [-h]
#?
#? Options:
#?   [-p]
#?
#?   Build the Docker images in parallel.
#?   This option implies `build --quiet` and `run --detach` to avoid the output mess.
#?   This option implies `run --publish-all` to avoid the port conflict.
#?
#?   [-P]
#?
#?   Enable to fetch the env `DOCKER_BUILD_ARGS_PROXY` and pass to docker build command.
#?   If the env `DOCKER_BUILD_ARGS_PROXY` is not set or empty, exit with error.
#?
#?   [-m]
#?
#?   Enable the multi-platform build for: linux/amd64, linux/arm64.
#?   This option implies `build --push --platform linux/amd64,linux/arm64`.
#?   WARNING: The images will be PUSHED to Docker Hub after the build.
#?
#?   As of the nature of the multi-platform build, at local, the multi-platform images
#?   will remain in the build cache, and won't be listed in the `docker images`.
#?   However, the image will be pulled as single-platform image from the registry in
#?   the subsequent `docker run` command.
#?   This option requires the non-default Docker builder driver: docker-container.
#?     * https://docs.docker.com/build/building/multi-platform/
#?     * docker buildx create --name container --driver=docker-container --use
#?
#?   [-d]
#?
#?   Run the container in the detach mode: `run --detach`
#?   This option implies `run --publish-all` to avoid the port conflict.
#?
#?   [DISTRIBUTION ..]
#?
#?   The distributions to build the Docker images for.
#?   The default is to build for all distributions: debian, slim, alpine.
#?
#?   [-- RUN_CMD_OPTIONS ..]
#?
#?   The option `--` ends the options for this script and enables the run command options.
#?   All the options after `--` are passed to the docker-entrypoint.sh.
#?   If the option `--` is not present, the run command is not executed.
#?
#?   [-h]
#?
#?   This help.
#?
#? Environment:
#?   The following environment variables are used by this script conditionally:
#?
#?   - DOCKER_BUILD_ARGS_PROXY="--build-arg http_proxy=http://host.docker.internal:1086 --build-arg https_proxy=http://host.docker.internal:1086 --build-arg all_proxy=socks5://host.docker.internal:1086"
#?
#?     Optional, default is unset.
#?     Set the proxy for the Docker build. Please replace the proxy port with your actual port.
#?

# exit on any error
set -e -o pipefail

function usage () {
    awk '/^#\?/ {sub("^[ ]*#\\?[ ]?", ""); print}' "$0" \
        | awk '{gsub(/^[^ ]+.*/, "\033[1m&\033[0m"); print}'
}

function check-vars () {
    declare var ret=0
    for var in "$@"; do
        if [[ -z ${!var} ]]; then
            echo "FATAL: environment variable $var is not set or empty." >&2
            (( ret++ ))
        fi
    done
    return $ret
}

function main () {
    declare build_parallel_flag=0 build_proxy_flag=0 build_multiple_platform_flag=0 \
            run_detach_flag=0 \
            build_quiet_flag=0 run_publish_all_flag=0 run_flag=0 \
            OPTIND OPTARG opt

    while getopts pPmdh opt; do
        case $opt in
            p)
                build_parallel_flag=1
                # implied options
                build_quiet_flag=1
                run_detach_flag=1
                run_publish_all_flag=1
                ;;
            P)
                build_proxy_flag=1
                ;;
            m)
                build_multiple_platform_flag=1
                ;;
            d)
                run_detach_flag=1
                # implied options
                run_publish_all_flag=1
                ;;
            *)
                usage
                return 255
                ;;
        esac
    done
    # shift off the parsed options
    shift $((OPTIND - 1))

    declare -a distributions run_cmd_opts

    # parse distributions
    while [[ $# -gt 0 && $1 != -* ]]; do
        distributions+=("$1")
        shift
    done

    if [[ $# -gt 0 ]]; then
        # shift off the '--' delimiter
        if [[ $1 == "--" ]]; then
            shift
        fi
        # The rest are docker run cmd options
        run_cmd_opts=("$@")
        run_flag=1
    fi

    # default distributions
    # shellcheck disable=SC2206
    distributions=(${distributions[*]:-debian slim alpine})

    declare -a build_opts \
               run_opts=(--restart=always) \
               run_env_opts \
               run_port_opts=(-p 80:80 -p 443:443)

    if [[ $build_multiple_platform_flag -eq 1 ]]; then
        build_opts+=(--push --platform "linux/amd64,linux/arm64")
        echo "WARNING: The multi-platform build is enabled, the images will be PUSHED to Docker Hub after the build."
    fi

    if [[ $build_quiet_flag -eq 1 ]]; then
        build_opts+=(--quiet)
    fi

    if [[ $run_detach_flag -eq 1 ]]; then
        run_opts+=(--detach)
    fi

    if [[ $run_publish_all_flag -eq 1 ]]; then
        run_port_opts=(--publish-all)
    fi

    if [[ $build_proxy_flag -eq 1 ]]; then
        check-vars DOCKER_BUILD_ARGS_PROXY
        # do not quote it
        # shellcheck disable=SC2206
        build_opts+=($DOCKER_BUILD_ARGS_PROXY)
    fi

    declare image_name=alexzhangs/shadowsocks-manager

    declare script_dir
    script_dir=$(dirname "$0")

    declare -a BUILD_OPTS RUN_OPTS

    function __build_and_run__ () {
        # build the image
        echo ""
        echo "INFO: docker buildx build ${BUILD_OPTS[*]}"
        docker buildx build "${BUILD_OPTS[@]}"

        if [[ $run_flag -eq 0 ]]; then
            return
        fi

        # run the container
        echo ""
        echo "INFO: docker run ${RUN_OPTS[*]}"
        docker run "${RUN_OPTS[@]}" || :
    }

    declare dist image_tag image container
    for dist in "${distributions[@]}"; do
        image_tag=$dist-dev-$(date -u +%Y%m%d-%H%M)
        image="$image_name:$image_tag"
        container="ssm-$image_tag"
        BUILD_OPTS=( "${build_opts[@]}" -t "$image" -f "$script_dir/docker/$dist/Dockerfile" . )
        RUN_OPTS=( "${run_opts[@]}" "${run_env_opts[@]}" "${run_port_opts[@]}" --name "$container" "$image" "${run_cmd_opts[@]}" )
        if [[ $build_parallel_flag -eq 1 ]]; then
            __build_and_run__ &
            # sleep a bit to avoid the output mess
            sleep 0.5
        else
            __build_and_run__
        fi
    done

    if [[ $build_parallel_flag -eq 1 ]]; then
        echo ""
        echo "INFO: Waiting for the parallel builds and runs to finish ..."
        wait
    fi
}

main "$@"

exit
