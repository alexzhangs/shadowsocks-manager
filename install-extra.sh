#!/bin/bash

# Exit on any error
set -o pipefail -e

yum install -y nginx
chkconfig nginx on
nginx -t && service nginx start

git clone --depth 1 https://github.com/alexzhangs/aws-ec2-supervisor
bash aws-ec2-supervisor/aws-ec2-supervisor-install.sh -i -v 4.0.3
chkconfig supervisord on
service supervisord start

yum install -y gcc
pip install uwsgi==2.0.18

exit
