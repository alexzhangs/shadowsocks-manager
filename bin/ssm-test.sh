#!/usr/bin/env bash

#? Description:
#?   Test shadowsocks-manager in your Python environment.
#?   If you need to run the setup under a specific Python environment, make
#?   sure to activate it before to run the setup.
#?
#? Usage:
#?   ssm-test.sh [-t] [-c] [-g [-o OUTFILE]] [-u] [-h]
#?
#? Options:
#?   [-t]
#?
#?   Run the test.
#?
#?   [-c]
#?
#?   Run the test with coverage.
#?
#?   [-g]
#?
#?   Generate coverage report with the previous coverage data.
#?
#?   [-o OUTFILE]
#?
#?   The output file for the coverage report.
#?   The default is `coverage.xml`.
#?
#?   [-u]
#?
#?   Upload the coverage report to codecov.io.
#?
#?   [-h]
#?
#?   This help.
#?
#? Environment:
#?   The following environment variables are used by this script:
#?
#?   - CODECOV_TOKEN
#?
#?     Required if -u is provided.
#?
#? Example:
#?   # run the test without coverage, and generate coverage report, and upload it
#?   $ ssm-test.sh -c -g -u
#?

# exit on any error
set -e -o pipefail

function usage () {
    awk '/^#\?/ {sub("^[ ]*#\\?[ ]?", ""); print}' "$0" \
        | awk '{gsub(/^[^ ]+.*/, "\033[1m&\033[0m"); print}'
}

function main () {
    declare test=0 coverage=0 report=0 outfile_opt upload=0 \
            OPTIND OPTARG opt

    while getopts tcgo:u opt; do
        case $opt in
            t)
                test=1
                ;;
            c)
                coverage=1
                ;;
            g)
                report=1
                ;;
            o)
                outfile_opt=(-o "$OPTARG")
                ;;
            u)
                upload=1
                ;;
            *)
                usage
                exit 255
                ;;
        esac
    done

    if [[ $# -eq 0 ]]; then
        usage
        exit 255
    fi

    # run the test
    if [[ ${test} -eq 1 ]]; then
        ssm-manage test --no-input -v 2
    fi

    # run the test with coverage
    if [[ ${coverage} -eq 1 ]]; then
        ssm coverage run manage.py test --no-input -v 2
    fi

    # generate coverage report
    if [[ ${report} -eq 1 ]]; then
        ssm coverage xml "${outfile_opt[@]}"
    fi

    # upload coverage report
    if [[ ${upload} -eq 1 ]]; then
        ssm codecovcli upload-process
    fi
}

main "$@"

exit
