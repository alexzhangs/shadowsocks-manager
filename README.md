# shadowsocks-manager

A web-based Shadowsocks management tool.

Features:

* Central user management
* Heartbeat on Shadowsocks ports(users)
* Shadowsocks multi-user API
* Shadowsocks node cluster
* Statistics for network traffic usage
* Scheduled jobs
* name.com API
* Auto-creating DNS records
* Production deployment ready

Code in Python, base on Django, Django REST framework, Celery, and SQLite.


## 1. Requirements

* Python 2.7
* macOS Big Sur (only the core python code tested, the installation scripts
  work on Linux only)
* AWS Amazon Linux AMI
* AWS Amazon Linux 2 AMI
* Shadowsocks-libev 3.2.0 for Linux (multi-user API is required)


## 2. Install with scripts

NOTE: It's better to install the project within a virtualenv.

Open a terminal on the server in which the shadowsocks-manager is going to run.

1. Get the code:

    ```sh
    git clone https://github.com/alexzhangs/shadowsocks-manager
    ```

1. Install

    The installation scripts can WORK ONLY ON LINUX and be tested only with Amazon Linux AMI and Amazon Linux 2 AMI.

    Run below commands under root, the order matters.

    ```sh
    # required, installing rabbitmq-server, Memcached, pip.
    bash shadowsocks-manager/install-dependency.sh

    # optional but recommended, installing Nginx, gcc, uwsgi, supervisor.
    bash shadowsocks-manager/install-extra.sh

    # required, installing shadowsocks-manager itself.
    bash shadowsocks-manager/install.sh
    ```

    If you want to customize the shadowsocks-manager installation, see: `bash shadowsocks-manager/install.sh -h`:

    ```
    Usage: install.sh [-n DOMAIN] [-u USERNAME] [-p PASSWORD] [-e EMAIL] [-t TIMEZONE] [-o PORT_BEGIN] [-O PORT_END]
    Run this script under root on Linux.
    OPTIONS
        [-n DOMAIN]

        Domain name resolved to the shadowsocks-manager web application.

        [-u USERNAME]

        Username for shadowsocks-manager administrator, default is 'admin'.

        [-p PASSWORD]

        Password for shadowsocks-manager administrator, default is 'passw0rd'.

        [-e EMAIL]

        Email for the shadowsocks-manager administrator.
        Also, be used as the sender of the account notification Email.

        [-t TIMEZONE]

        Set Django's timezone, default is 'UTC'.
        Statistics period also senses this setting. Note that AWS billing is based on UTC.

        [-r PORT_BEGIN]

        Port range allowed for all Shadowsocks nodes.

        [-R PORT_END]

        Port range allowed for all Shadowsocks nodes.

        [-h]

        This help.
    ```

1. Start and reload the services.

    If goes with `install-extra.sh`, then reload the supervisor vendors and Nginx:

    ```
    supervisorctl reload
    service nginx reload
    ```

    If goes without `install-extra.sh`, then jump to `4.3 Start services manually (without install-extra.sh)` to finish all steps, then come back and go on.

1. Verify the installation

    If all go smoothly, the shadowsocks-manager services should have been all started. Open the web admin console in a web browser, and log on with the admin user.

    Use:
    ```
    http://<your_server_ip>/admin
    ```
    Or:
    ```
    http://<your_server_ip>:8000/admin
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


## 4. Install without scripts (manually)

### 4.1 Dependency

1. RabbitMQ

    RabbitMQ is used as a Celery broker to distribute scheduled jobs for
necessary maintenance, such as traffic statistics and port heartbeat.

    ```sh
    # on macOS
    brew install rabbitmq
    brew services start rabbitmq

    # on Linux
    yum install rabbitmq-server
    service rabbitmq-server start
    chkconfig --add rabbitmq-server
    ```

1. Memcached

    Memcached is used as the Django cache backend. It's required by
normal Django cache, singleton model, and global exclusive lock.

    ```sh
    # on macOS
    brew install memcached
    brew services start memcached

    # on Linux
    yum install memcached
    service memcached start
    chkconfig --add memcached
    ```

1. Sendmail (Optional)

    `sendmail` is used to send account notification Email, it should
be configured on the same server with shadowsocks-manager.

    About how to configure `sendmail` client to use AWS SES as SMTP server on AWS EC2 instance, refer to repo
[aws-ec2-ses](https://github.com/alexzhangs/aws-ec2-ses).

    On macOS, refer to repo
[macos-aws-ses](https://github.com/alexzhangs/macos-aws-ses).

    NOTE: This dependency needs the manual setup anyway, it is not handled by any installation script.

### 4.2 For the Production Deployment

For the production deployment, Nginx, uwsgi, supervisor are
recommended. They are handled by the script `install-extra.sh`.

If you proceed without the script, some of the commands mentioned in this document won't be available.

### 4.3 Start services manually (without install-extra.sh)

1. Start web application

    ```sh
    python manage.py runserver <your_server_ip>:8000 --insecure
    ```

1. Start the scheduled jobs

    Start Worker and Beat together:

    ```sh
    celery -A shadowsocks_manager worker -l info -B
    ```

    Start Worker and Beat with separate processes, this is recommended for production deployment:

    ```sh
    celery -A shadowsocks_manager worker -l info
    celery -A shadowsocks_manager beat -l info
    ```


## 5. Can the installation be easier?

Yes, if you are deploying the services in the AWS.

[aws-cfn-vpn](https://github.com/alexzhangs/aws-cfn-vpn)
is a set of AWS CloudFormation templates which let you
deploy VPN services, including Shadowsocks (support cluster) and
XL2TPD, with a single click. Also, this repo, shadowsocks-manager and
all its dependencies are handled by `aws-cfn-vpn`.


## 6. Differences from the alternation: [shadowsocks/shadowsocks-manager](https://github.com/shadowsocks/shadowsocks-manager)

**This repo Do's:**

* Serve as a nonprofit business model.
* Have central user management for multi nodes.
* Collect traffic statistics that can be viewed by account, node, and period.
* Show the existence and accessibility of ports in the admin.
* Handle the DNS records if using Name.com as nameserver.

**This repo Don'ts:**

* Handle self-serviced user registration.
* Handle bill or payment.
* Need to run an additional agent on each Shadowsocks server.


## 7. Known Issues

1. DNS records matching for Node may not be accurate on macOS.
    For unknown reason sometimes DNS query returns only one IP address
while multiple IP addresses were configured for the domain.


## 8. Troubleshooting

1. Check the logs (with install-extra.sh)

    ```
    # supervisor
    cat /tmp/supervisord.log

    # uWSGI
    cat /var/log/ssm-uwsgi.log

    # Celery
    cat /var/log/ssm-cerlery*
    ```

1. Check the services (with install-extra.sh)

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


## 9. TODO

* Auto deactivate/activate nodes based on traffic usage and quota.
* Support LDAP.
