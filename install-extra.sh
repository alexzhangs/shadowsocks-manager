#!/bin/bash

#? Description:
#?   Install the extra packages for shadowsocks-manager.
#?   Run this script under root on Linux.
#?
#?   Below packages are recommended for the production deployment.
#?     * gcc (for building uwsgi)
#?     * nginx (web server)
#?     * supervisor (to supervise the process of uwsgi and celery)
#?
#? Usage:
#?   install-extra.sh
#?
declare WORK_DIR=$(cd "$(dirname "$0")"; pwd)
source "$WORK_DIR/common.sh"

function main () {
    # install gcc
    xsh aws/gist/ec2/linux/yum/install gcc

    # install nginx, set autostart, and start the service
    xsh aws/gist/ec2/linux/yum/install -o -s nginx

    # install supervisor, add InitScript, set autostart, and start the service
    xsh aws/gist/ec2/linux/installer/supervisor -i -o -s -v 4.0.3
}

install-xsh

main "$@"

exit
