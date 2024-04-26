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
        * Pre-installed, and have a builtin service manager.

Code in Python, base on Django, Django REST framework, Celery, and SQLite.

The development status can be found at: [project home](https://github.com/alexzhangs/shadowsocks-manager/projects/1).

Node List:
![Home › Shadowsocks › Shadowsocks Nodes](https://www.0xbeta.com/shadowsocks-manager/assets/images/shadowsocks-node-list.png)

Node's Shadowsocks Manager:
![Home › Shadowsocks › Shadowsocks Nodes](https://www.0xbeta.com/shadowsocks-manager/assets/images/shadowsocks-node-ssmanager.png)


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
docker run -d -p 11211:11211 --network ssm-network --name ssm-memcached memcached

# run rabbitmq, used by celery
docker run -d -p 5672:5672 --network ssm-network --name ssm-rabbitmq rabbitmq

# create a directory to store the data, it will be mounted to the container
mkdir -p ~/ssm-volume

# run the shadowsocks-manager
docker run -d -p 80:80 --network ssm-network -v ~/ssm-volume:/var/local/ssm --name ssm alexzhangs/shadowsocks-manager \
           -e SSM_SECRET_KEY=yourkey -e SSM_DEBUG=False -e SSM_MEMCACHED_HOST=ssm-memcached -e SSM_RABBITMQ_HOST=ssm-rabbitmq \
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

    About how to install and configure Shadowsocks server in AWS, refer
to the repo
[aws-ec2-shadowsocks-libev](https://github.com/alexzhangs/aws-ec2-shadowsocks-libev)

    After the server is installed and started, there should be a
running process named `ss-manager`. Write down the IP address and
the port that the `ss-manager` is listening on, and also the public IP
address of the server, the encryption method that Shadowsocks is using,
they are going to be used in the next step.

1. Add Shadowsocks server to shadowsocks-manager

    Add the Shadowsocks server as a Node of shadowsocks-manager from
web admin console: `Home › Shadowsocks › Shadowsocks Nodes`.

1. Create users(ports) and assign Shadowsocks Node

    Create users from web admin console: `Home › Shadowsocks ›
Shadowsocks Accounts` and assign the existing nodes to them.

    After a few seconds, the created user ports should be available to your
Shadowsocks client.

1. The builtin local service manager for Shadowsocks python edition

    There's a builtin local service manager available for the Shadowsocks `python edition`. 

    The `python edition` is pre-installed with `shadowsocks-manager`. With the service manager, you can start&stop
the local service daemon on-the-fly. Check it out from the web admin console `Home › Shadowsocks › Shadowsocks Nodes`, 
under the `SHADOWSOCKS MANAGERS` tab.

    However the `traffice statistics` and `user port creation status` features are not available for the 
`python edition`.


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

### Update for Shadowsocks Python edition on 2024-04

Both the pypi version (2.8.2) and the github master branch (3.0.0) failed to start `ssserver` due to the upstream and dependency changes.

Since the Python edition is pre-installed in this project, mainly for running test cases, I have to make a patch to make it work.

The fix based on github master branch 3.0.0, and would be minimal, just to make the `ssserver` start without any error, no more features added.
After the fix, the pre-installed Python edition will be changed from the [original pypi version](https://pypi.org/project/shadowsocks/) to [my fork](https://pypi.org/project/shadowsocks-alexforks/).


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
    docker run -d -p 11211:11211 --name ssm-memcached memcached

    # run rabbitmq, used by celery
    docker run -d -p 5672:5672 --name ssm-rabbitmq rabbitmq
    ```

1. Link the project code in your workspace to the Python environment

    ```sh
    cd shadowsocks-manager
    pip install -e .
    ```

1. Configure the shadowsocks-manager

    ```sh
    ssm-setup -c -m -l -u admin -p yourpassword
    ```

1. Run the development server

    ```sh
    ssm-dev-start
    ```

1. Stop the development server

    ```sh
    ssm-dev-stop
    ```

1. Test the Django code

    ```sh
    ssm-test -t
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
    ```

1. Check the listening ports (Linux)

    ```
    # TCP
    netstat -tan

    # UDP
    netstat -uan
    ```
