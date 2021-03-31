#!/bin/bash

#? Description:
#?   Install the external packages depended by shadowsocks-manager.
#?   Run this script under root on Linux.
#?
#?   Below packages are neccessary to run shadowsocks-manager.
#?     * rabbitmq-server
#?     * memcached
#?     * pip
#?     * virtualenv
#?
#? Usage:
#?   install-dependency.sh
#?
declare WORK_DIR=$(cd "$(dirname "$0")"; pwd)
source "$WORK_DIR/common.sh"

function main () {
    # add or enable yum repo `epel` if available
    amazon-linux-extras install -y epel || yum-config-manager --enable epel || :

    # install rabbitmq-server and memcached
    xsh aws/gist/ec2/linux/yum/install -o -s rabbitmq-server memcached

    # install pip
    xsh aws/gist/ec2/linux/installer/pip

    # install virtualenv
    pip install virtualenv
}

main "$@"

exit
