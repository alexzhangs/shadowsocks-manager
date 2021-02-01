#!/bin/bash

# Exit on any error
set -o pipefail -e

yum install -y rabbitmq-server --enablerepo=epel
chkconfig rabbitmq-server on
service rabbitmq-server start

yum install -y memcached
chkconfig memcached on
service memcached start

exit
