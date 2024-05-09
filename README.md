[![License](https://img.shields.io/github/license/alexzhangs/shadowsocks-manager.svg?style=flat-square)](https://github.com/alexzhangs/shadowsocks-manager/)
[![GitHub last commit](https://img.shields.io/github/last-commit/alexzhangs/shadowsocks-manager.svg?style=flat-square)](https://github.com/alexzhangs/shadowsocks-manager/commits/master)
[![GitHub issues](https://img.shields.io/github/issues/alexzhangs/shadowsocks-manager.svg?style=flat-square)](https://github.com/alexzhangs/shadowsocks-manager/issues)
[![GitHub pull requests](https://img.shields.io/github/issues-pr/alexzhangs/shadowsocks-manager.svg?style=flat-square)](https://github.com/alexzhangs/shadowsocks-manager/pulls)
[![GitHub tag](https://img.shields.io/github/v/tag/alexzhangs/shadowsocks-manager?sort=date)](https://github.com/alexzhangs/shadowsocks-manager/tags)

[![GitHub Actions - CI Unit test](https://github.com/alexzhangs/shadowsocks-manager/actions/workflows/ci-unittest.yml/badge.svg)](https://github.com/alexzhangs/shadowsocks-manager/actions/workflows/ci-unittest.yml)
[![GitHub Actions - CI TestPyPI](https://github.com/alexzhangs/shadowsocks-manager/actions/workflows/ci-testpypi.yml/badge.svg)](https://github.com/alexzhangs/shadowsocks-manager/actions/workflows/ci-testpypi.yml)
[![GitHub Actions - CI PyPI](https://github.com/alexzhangs/shadowsocks-manager/actions/workflows/ci-pypi.yml/badge.svg)](https://github.com/alexzhangs/shadowsocks-manager/actions/workflows/ci-pypi.yml)
[![PyPI Package Version](https://badge.fury.io/py/shadowsocks-manager.svg)](https://pypi.org/project/shadowsocks-manager/)
[![codecov](https://codecov.io/gh/alexzhangs/shadowsocks-manager/graph/badge.svg?token=KTI3TNRKAV)](https://codecov.io/gh/alexzhangs/shadowsocks-manager)

[![GitHub Actions - CI Docker Build and Push](https://github.com/alexzhangs/shadowsocks-manager/actions/workflows/ci-docker.yml/badge.svg)](https://github.com/alexzhangs/shadowsocks-manager/actions/workflows/ci-docker.yml)
[![Docker Image Version](https://img.shields.io/docker/v/alexzhangs/shadowsocks-manager?label=docker%20image)](https://hub.docker.com/r/alexzhangs/shadowsocks-manager)

# shadowsocks-manager

A web-based Shadowsocks management tool.

Features:

* Central user management
* Heartbeat on Shadowsocks ports(users)
* Shadowsocks multi-user API
* Shadowsocks node cluster
* Statistic for network traffic usage
* Scheduled jobs
* name.com API
* Auto-creating DNS records
* Production deployment ready
* How's the Shadowsocks supported:
    * libev edition:
        * Full functional.
        * No builtin service manager, you need to install it and start the service by yourself.
    * python edition:
        * Lacks the collection of traffic statistics.
        * Lacks the ability to test user port creation status.
        * ~~Pre-installed, and have a builtin service manager.~~
        * No builtin service manager, you need to install it and start the service by yourself.

Code in Python, base on Django, Django REST framework, Celery, and SQLite.

The development status can be found at: [project home](https://github.com/alexzhangs/shadowsocks-manager/projects/1).


## Screenshots

Shadowsocks Node List:
![Home › Shadowsocks › Shadowsocks Nodes](https://www.0xbeta.com/shadowsocks-manager/assets/images/shadowsocks-node-list.png)

Add Shadowsocks Node:
![Home › Shadowsocks › Shadowsocks Nodes](https://www.0xbeta.com/shadowsocks-manager/assets/images/shadowsocks-node-add.png)

Add Shadowsocks Account:
![Home › Shadowsocks › Shadowsocks Accounts](https://www.0xbeta.com/shadowsocks-manager/assets/images/shadowsocks-account-add.png)


## 1. Requirements

* Python 2.7, Python 3.x
* Django 1.11.x, Django 3.x
* Docker
* [Shadowsocks-libev 3.2.0 for Linux (multi-user API is required)](https://github.com/shadowsocks/shadowsocks-libev)


## 2. Install

This project is a part of an entire VPN solution, which includes the Shadowsocks server and Shadowsocks manager. The Shadowsocks server serves the traffic, the Shadowsocks manager serves the users and the traffic statistics. The solution is designed to be deployed in the AWS cloud. If you are looking for such a solution, you can refer to the repo [aws-cfn-vpn](https://github.com/alexzhangs/aws-cfn-vpn). With `aws-cfn-vpn`, you can deploy the entire solution with a few commands.

### 2.1. Dependencies

Assume you have installed the [Docker](https://www.docker.com/) on your host.

### 2.2. Manual installation

```sh
# create a docker network
docker network create ssm-network

# run memcached, used by django cache
docker run -d --network ssm-network --name ssm-memcached memcached

# run rabbitmq, used by celery
docker run -d --network ssm-network --name ssm-rabbitmq rabbitmq

# create a directory to store the data, it will be mounted to the shadowsocks-manager container
mkdir -p ~/ssm-volume

# run the shadowsocks-manager
docker run -d -p 80:80 -v ~/ssm-volume:/var/local/ssm \
    --network ssm-network --name ssm alexzhangs/shadowsocks-manager \
    -e SSM_SECRET_KEY=yourkey -e SSM_DEBUG=False \
    -e SSM_MEMCACHED_HOST=ssm-memcached -e SSM_RABBITMQ_HOST=ssm-rabbitmq \
    -u admin -p yourpassword -M admin@yourdomain.com
```

### 2.3. Install with script

```sh
git clone https://github.com/alexzhangs/shadowsocks-manager
bash shadowsocks-manager/install.sh -u admin -p yourpassword -M admin@yourdomain.com
```

### 2.4. Verify the installation

If all go smoothly, the shadowsocks-manager services should have been all started. Open the web admin console in a web browser, and log on with the admin user.

Use:
```
http://<your_server_ip>/admin
or 
http://localhost/admin
```

If goes well, then congratulations! The installation has succeeded.


## 3. Using shadowsocks-manager

1. Shadowsocks server

    First, you need to have a Shadowsocks server with the multi-user API
enabled.

    Install it with docker on the same server with shadowsocks-manager.

    ```sh
    # run shadowsocks-libev
    MGR_PORT=6001
    SS_PORTS=8381-8480
    ENCRYPT=aes-256-cfb
    docker run -d -p $SS_PORTS:$SS_PORTS/UDP -p $SS_PORTS:$SS_PORTS \
        --network ssm-network --name ssm-ss-libev shadowsocks/shadowsocks-libev:edge \
        ss-manager --manager-address 0.0.0.0:$MGR_PORT \
        --executable /usr/local/bin/ss-server -m $ENCRYPT -s 0.0.0.0 -u

    # Use below command to get the private IP address of the shadowsocks-libev container for later configuration.
    docker inspect ssm-ss-libev | grep IPAddress
    ```

1. Add Shadowsocks server to shadowsocks-manager

    Add the Shadowsocks server as a Node of shadowsocks-manager from
web admin console: `Home › Shadowsocks › Shadowsocks Nodes`.

1. Create users(ports) and assign Shadowsocks Node

    Create users from web admin console: `Home › Shadowsocks ›
Shadowsocks Accounts` and assign the existing nodes to them.

    After a few seconds, the created user ports should be available to your
Shadowsocks client.


## 4. Sendmail (Optional)

`sendmail` is used to send account notification Email, it should
be configured on the same server with shadowsocks-manager.

About how to configure `sendmail` client to use AWS SES as SMTP server on AWS EC2 instance, refer to repo
[aws-ec2-ses](https://github.com/alexzhangs/aws-ec2-ses).

On macOS, refer to repo
[macos-aws-ses](https://github.com/alexzhangs/macos-aws-ses).

NOTE: This dependency needs the manual setup anyway, it is not handled by any installation script.


## 5. Differences from the alternation: [shadowsocks/shadowsocks-manager](https://github.com/shadowsocks/shadowsocks-manager)

**This repo Do's:**

* Serve as a nonprofit business model.
* Have central user management for multi nodes.
* Collect traffic statistic that can be viewed by account, node, and period.
* Show the existence and accessibility of ports in the admin.
* Handle the DNS records if using Name.com as nameserver.

**This repo Don'ts:**

* Handle self-serviced user registration.
* Handle bill or payment.
* Need to run an additional agent on each Shadowsocks server.


## 6. Some differences between the Shadowsocks Python edition (2.8.2) and libev edition

Version status for the Shadowsocks Python edition:
* pypi: [2.8.2](https://pypi.org/project/shadowsocks/)
* github: [3.0.0](https://github.com/shadowsocks/shadowsocks/tree/master)

Although the Shadowsocks Python edition
supports the multi-user API, but it doesn't fit this project, here's why:

* The python edition code and doc seem to be out of maintenance due to some reason. If you really need this you probably need to fork it and make your own.
* They are having different service process names and CLI interfaces which introduces the complexity of installation.
* The Python edition lacks the `list` commands. A pull request was opened years ago but never merged.
* The Python edition's `stat` command has a very different way to use, I didn't figure the usage syntax out by looking into the code.
* The Python edition's `ping` command returns a simple string `pong` rather than a list of ports.
* The Python edition's `ping` command has to be sent as the syntax: `ping:{}` in order to work if tested with `nc`. It caused by the tailing newline: `ping\n`.

So either you get some change on your own or stick with the libev edition.


## 7. Known Issues

1. DNS records matching for Node may not be accurate on macOS.
    For unknown reason sometimes DNS query returns only one IP address
while multiple IP addresses were configured for the domain.

1. The Shadowsocks Python edition's ssserver won't start on macOS.
    The error message is like:
    ```
    $ ssserver -k passw0rd
    WARNING: /Users/***/.pyenv/versions/3.12.0/envs/ssm-3.12/bin/python3.12 is loading libcrypto in an unsafe way
    Abort trap: 6
    ```

    Solution:
    Link the homebrew openssl library to the system library.
    ```sh
    sudo ln -s /opt/homebrew/opt/openssl/lib/libcrypto.dylib /usr/local/lib/
    sudo ln -s /opt/homebrew/opt/openssl/lib/libssl.dylib /usr/local/lib/
    ```

1. Install the project by source with pip under Python 2.7 get error:
    ```
    python --version
    Python 2.7.18

    pip install .
    ```

    Error message:
    ```
    ...
    Collecting pyyaml
    Downloading PyYAML-5.4.1.tar.gz (175 kB)
        |████████████████████████████████| 175 kB 392 kB/s 
    Installing build dependencies ... done
    Getting requirements to build wheel ... error
    ERROR: Command errored out with exit status 1:
    ...
        raise AttributeError, attr
    AttributeError: cython_sources
    ...
    ```

    Solution:
    ```sh
    pip install setuptools wheel
    pip install --no-build-isolation .
    ```


## 8. Development

The development of this project requires Python 3.x.

However, the installation of the project is compatible with both Python 2.7 and 3.x.
To keep the compatibility is difficult, but it's kept due to the historical reason.
The following files are kept only for installing the source distribution of the PyPI package under Python 2.7:

* setup.py
* setup.cfg

### 8.1. Development Environment Setup

1. Install the dependencies

    ```sh
    # run memcached, used by django cache
    docker run -d -p 11211:11211 --name ssm-dev-memcached memcached

    # run rabbitmq, used by celery
    docker run -d -p 5672:5672 --name ssm-dev-rabbitmq rabbitmq

    # run shadowsocks-libev, simulate localhost node
    MGR_PORT=6001 SS_PORTS=8381-8479 ENCRYPT=aes-256-cfb
    docker run -d -p 127.0.0.1:$MGR_PORT:$MGR_PORT/UDP \
        -p 127.0.0.1:$SS_PORTS:$SS_PORTS/UDP -p 127.0.0.1:$SS_PORTS:$SS_PORTS \
        --name ssm-dev-ss-libev-localhost shadowsocks/shadowsocks-libev:edge \
        ss-manager --manager-address 0.0.0.0:$MGR_PORT \
        --executable /usr/local/bin/ss-server -m $ENCRYPT -s 0.0.0.0 -u

    # get the private IP address of the host, double check the result, it might not be correct
    PRIVATE_IP=$(ipconfig getifaddr en0 2>/dev/null || hostname -i | awk '{print $1}' 2>/dev/null)
    echo "PRIVATE_IP=$PRIVATE_IP"

    # run shadowsocks-libev, simulate private IP node
    MGR_PORT=6002 SS_PORTS=8381-8479 ENCRYPT=aes-256-cfb
    docker run -d -p $PRIVATE_IP:$MGR_PORT:$MGR_PORT/UDP \
        -p $PRIVATE_IP:$SS_PORTS:$SS_PORTS/UDP -p $PRIVATE_IP:$SS_PORTS:$SS_PORTS \
        --name ssm-dev-ss-libev-private shadowsocks/shadowsocks-libev:edge \
        ss-manager --manager-address 0.0.0.0:$MGR_PORT \
        --executable /usr/local/bin/ss-server -m $ENCRYPT -s 0.0.0.0 -u
        
    # run shadowsocks-libev, simulate public IP node
    MGR_PORT=6003 SS_PORTS=8480 ENCRYPT=aes-256-cfb
    docker run -d -p $PRIVATE_IP:$MGR_PORT:$MGR_PORT/UDP \
        -p $PRIVATE_IP:$SS_PORTS:$SS_PORTS/UDP -p $PRIVATE_IP:$SS_PORTS:$SS_PORTS \
        --name ssm-dev-ss-libev-public shadowsocks/shadowsocks-libev:edge \
        ss-manager --manager-address 0.0.0.0:$MGR_PORT \
        --executable /usr/local/bin/ss-server -m $ENCRYPT -s 0.0.0.0 -u
    ```

1. Link the project code in your workspace to the Python environment

    ```sh
    cd shadowsocks-manager
    pip install -e .
    ```

1. Set the SSM_DATA_HOME environment variable (optional, default is Django root directory)

    ```sh
    export SSM_DATA_HOME=~/.ssm-dev-data
    ```

1. Configure the shadowsocks-manager

    ```sh
    ssm-setup -c -m -l -u admin -p yourpassword
    ```

1. Run the development server

    Make sure the memcached and rabbitmq are running.

    ```sh
    ssm-dev-start
    ```

1. Stop the development server

    ```sh
    ssm-dev-stop
    ```

1. Test the Django code

    Make sure the memcached and rabbitmq are running, and also the 3 shadowsocks-libev node are running.

    ```sh
    ssm-test -t

    # or use the django test command directly for more options
    ssm-manage test --no-input -v 2
    ```

1. Test the Django code with coverage

    ```sh
    pip install coverage
    ssm-test -c
    ```

1. Upload the coverage report to codecov

    Make sure the `CODECOV_TOKEN` is exported in the environment before uploading.

    ```sh
    pip install codecov-cli
    ssm-test -u
    ```

1. Test the Github workflows locally

    ```sh
    brew install act
    act -j test
    ```

1. Build the PyPI package

    ```sh
    pip install build

    # build source and binary distribution, equivalent to `python setup.py sdist bdist_wheel`
    # universal wheel is enabled in the pyproject.toml to make the wheel compatible with both Python 2 and 3
    python -m build
    ```

1. Upload the PyPI package

    Set the ~/.pypirc file with the API token from the TestPyPI and PyPI before uploading.

    ```sh
    pip install twine

    # upload the package to TestPyPI
    python -m twine upload --repository testpypi dist/*

    # upload the package to PyPI
    python -m twine upload dist/*
    ```

1. Test the PyPI package

    ```sh
    # install the package from TestPyPI
    # --no-deps is used to skip installing dependencies for the TestPyPI environment
    pip install -i https://test.pypi.org/simple/ --no-deps shadowsocks-manager

    # install the package from PyPI
    # --no-binary is used to force building the package from the source
    # --use-pep517 is used together to make sure the PEP 517 is tested
    pip install --no-binary shadowsocks-manager --use-pep517 shadowsocks-manager
    ```

1. Build the docker image

    ```sh
    docker build -t alexzhangs/shadowsocks-manager .
    ```

### 8.2. CI/CD

Github Actions is currently used for the CI/CD.
Travis CI is removed due to the limitation of the free plan.

The CI/CD workflows are defined in the `.github/workflows` directory.

* ci-unittest.yml: Run the unit tests.
* ci-testpypi.yml: Build and upload the package to TestPyPI.
* ci-pypi.yml: Build and upload the package to PyPI. It can be triggered by the tag: `ci-pypi` or `ci-pypi-(major|minor|patch|suffx)`.
* ci-docker.yml: Build and push the docker image to Docker Hub. It can be triggered by the Github release.


## 9. Troubleshooting

1. Check the logs

    ```
    # supervisor
    cat /var/log/supervisor/supervisord.log

    # uWSGI
    cat /var/log/ssm-uwsgi.log

    # Celery
    cat /var/log/ssm-cerlery*
    ```

1. Check the services

    ```
    # nginx
    service nginx {status|start|stop|reload}

    # supervisor
    service supervisord {status|start|stop|restart}
    supervisorctl reload
    supervisorctl start all

    # uWSGI
    supervisorctl start ssm-uwsgi

    # Celery
    supervisorctl start ssm-celery-worker
    supervisorctl start ssm-celery-beat

    # Docker
    docker ps
    ```

1. Check the listening ports and processes (Linux)

    ```
    # TCP
    netstat -tanp

    # UDP
    netstat -uanp
    ```

1. Check the listening ports (MacOS)

    ```
    # TCP
    netstat -anp tcp

    # UDP
    netstat -anp udp

    # find the process by port
    lsof -i :80 -P
    ```