#!/bin/bash

## Install the external packages depended by shadowsocks-manager.
## Below packages are neccessary to run shadowsocks-manager.
##
##   * rabbitmq-server
##   * memecached
##   * pip
##

# Exit on any error
set -o pipefail -e

if [[ $(uname) != 'Linux' ]]; then
    printf "Error: this script support Linux only.\n" >&2
    exit 9
fi

# install pip if missing
# Amazon Linux 2 AMI needs this
if ! type pip >/dev/null 2>&1; then
    python_version=$(python --version 2>&1)
    python_version=${version:7:1}

    if [[ $python_version -eq 2 ]]; then
        # We can't install the latest version of pip here but to a version < 21.
        # pip dropped support for Python 2.7 since Jan, 2021. Amazon Linux and Linux 2
        # AMIs are still using Python 2.7.
        curl https://bootstrap.pypa.io/2.7/get-pip.py -o get-pip.py
    else
        # Get the latest version of pip.
        curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
    fi
    python get-pip.py
fi

# install yum repo: repl
# Amazon Linux 2 AMI needs this
if type amazon-linux-extras >/dev/null 2>&1; then
    amazon-linux-extras install -y epel
fi

# rabbitmq-server
yum install -y rabbitmq-server --enablerepo=epel
chkconfig rabbitmq-server on
service rabbitmq-server start

# memcached
yum install -y memcached
chkconfig memcached on
service memcached start

exit
