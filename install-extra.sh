#!/bin/bash

## Install the extra packages for shadowsocks-manager.
## Below packages are recommended for the production deployment.
## 
##   * nginx (web server)
##   * uwsgi (application server)
##   * gcc (for building uwsgi)
##   * supervisor (to supervise the process of uwsgi and celery)
##

# Exit on any error
set -o pipefail -e

if [[ $(uname) != 'Linux' ]]; then
    printf "Error: this script support Linux only.\n" >&2
    exit 9
fi

# nginx
yum install -y nginx
chkconfig nginx on
nginx -t && service nginx start

# supervisor
git clone --depth 1 https://github.com/alexzhangs/aws-ec2-supervisor
bash aws-ec2-supervisor/aws-ec2-supervisor-install.sh -i -v 4.0.3
chkconfig supervisord on
service supervisord start

# gcc and uwsgi
yum install -y gcc
pip install uwsgi==2.0.18

exit
