# shadowsocks-manager

A Shadowsocks management tool for multi user and traffic statistics,
support multi node, sync IPs to name.com.
Writen in Python, base on Django/DRF and SQLite.

It relies on Shadowsocks Multi-User API, which is only
supported by Shadowsocks libev and Python version by now.

Related repo: [aws-cfn-vpn](https://github.com/alexzhangs/aws-cfn-vpn)
aws-cfn-vpn is a set of AWS CloudFormation templates which let you
deploy VPN services, including Shadowsocks (support cluster) and XL2TPD, with a single
click. Also, this repo, shadowsocks-manager and all its dependencies
are handled by aws-cfn-vpn. If you are choosing AWS along with
Shadowsocks or XL2TPD, aws-cfn-vpn may save your time.


## Requirements

This repo is tested under:

* AWS Amazon Linux (Not the Amazon Linux 2) and macOS High Sierra
* Python 2.7
* Shadowsocks-libev 3.2.0 for Linux


## Dependencies

Following dependences need the addtional installation and
configuration, the details are out of scope for this document.

1. Shadowsocks

    Install Shadowsocks server on one or more server and start the
    service, there should be a running process named `ss-manager`.

    Write down following info of each server for later use:

    * Public IP address
    * IP address and port that `ss-manager` is listening on

    About how to install and configure Shadowsocks server in AWS , refer
    to repo
    [aws-ec2-shadowsocks-libev](https://github.com/alexzhangs/aws-ec2-shadowsocks-libev)


2. RabbitMQ

    RabbitMQ is used as Celery broker to distribute scheduled jobs for
    necessary maintenance, such as traffic statistics and port
    heartbeat.

    **macOS**

    ```
    brew install rabbitmq
    brew services start rabbitmq
    ```

    **Linux**

    ```
    yum install rabbitmq-server
    service rabbitmq-server start
    chkconfig --add rabbitmq-server
    ```

3. Memcached

    Memcached is used as the Django cache backend. It's requied by
    normal Django cache, singleton model and global exclusive lock.

    **macOS**

    ```
    brew install memcached
    brew services start memcached
    ```

    **Linux**

    ```
    yum install memcached
    service memcached start
    chkconfig --add memcached
    ```

4. gcc

    gcc is required while installing uWSGI with pip.

    ** Linux**

    ```
    yum install gcc
    ```

5. Sendmail (Optional)

    `sendmail` is used to send account notification Email, it should
    be configured on the same server if you want this feature.

    About how to configure sendmail client to use AWS SES as SMTP
    server on AWS EC2 instance, refer to repo
    [aws-ec2-ses](https://github.com/alexzhangs/aws-ec2-ses).

    On macOS, refer to repo
    [macos-aws-ses](https://github.com/alexzhangs/macos-aws-ses).


## Install shadowsocks-manager

It's better to install the project within a virtualenv.

### Get the code:

```
git clone https://github.com/alexzhangs/shadowsocks-manager
```

### Install it with script

This script works only under Linux.

```
bash shadowsocks-manager/install.sh -h
```

### Install it manually

1. Install Python dependencies:

    ```
    cd shadowsocks-manager
    pip install -r requirements.txt
    ```

1. Update Django settings

    **DEBUG**

    Change [DEBUG](https://docs.djangoproject.com/en/2.2/ref/settings/#std:setting-DEBUG)
    from True to Fasle for production deployment.

    ```
    DEBUG = False
    ```

    **ALLOWED_HOSTS**

    Add your domain that is resolved to shadowsocks-manager web
    application or the IP address if without a domain to
    [ALLOWED_HOSTS](https://docs.djangoproject.com/en/2.2/ref/settings/#allowed-hosts).

    Also adding both domain and IP is just find.

    ```
    ALLOWED_HOSTS = ['your_server_ip',  'yourdomain.com']
    ```

    **STATIC_ROOT**

    Set [STATIC_ROOT](https://docs.djangoproject.com/en/2.2/ref/settings/#static-root)
    for Django's static files.

    ```
    STATIC_ROOT = '/path_to_your_static_dir/
    ```

    **SECRET_KEY**

    Set your own
    [SECRET_KEY](https://docs.djangoproject.com/en/2.2/ref/settings/#std:setting-SECRET_KEY)
    other than the key from repo is strongly recommended.

    ```
    SECRET_KEY = 'your_own_secret_key'
    ```

    **TIME_ZONE**

     Optionally, set your prefered
    [TIME_ZONE](https://docs.djangoproject.com/en/2.2/ref/settings/#std:setting-TIME_ZONE).
    Statistics period also sences this setting. AWS billing is based on UTC.

    ```
    TIME_ZONE = 'your_prefered_timezone'
    ```

 1. Create database and load the fixtures:

    ```
    cd shadowsocks_manager
    python manage.py makemigrations
    python manage.py migrate
    python manage.py loaddata auth.group.json \
        django_celery_beat.crontabschedule.json \
        django_celery_beat.intervalschedule.json \
        django_celery_beat.periodictask.json \
        config.json \
        template.json
    ```

1. Create an administrator user for the web admin:

    This user would be used for logging into the web admin to manage
    Shadowsocks. Laterly should avoid reuse it as Shadowsocks user, but
    it's possible.

    Note: The admin that is logged in would be used as Email sender for
    account notification Email. Please properly set the Email and
    laterly set the fullname in the web admin.

    Example commands:

    ```
    python manage.py createsuperuser --username admin --email \
        admin@vpn.yourdomain.com --noinput
    ```

    Set a password for the user:

    ```
    python manage.py changepassword admin
    ```

1. Collect static files to `STATIC_ROOT`:

    ```
    python manage.py collectstatic
    ```


## Start shadowsocks-manager

### Start services with script

If you were using manual installation, you won't be able to use
following scripts.

1. Start shadowsocks-manager web application:

    ```
    sudo service shadowsocks-manager-web start
    ```

1. Start shadowsocks-manager scheduled jobs:

    ```
    sudo service shadowsocks-manager-job start
    ```

1. Set the services to start with OS boot:

    ```
    sudo chkconfig shadowsocks-manager-web on
    sudo chkconfig shadowsocks-manager-job on
    ```

### Start  services manually

1. Start web application

    ```
    python manage.py runserver <your_server_ip>:8000 --insecure
    ```

1. Log on the web admin with the created superuser at:

    ```
    http://<your_server_ip>:8000/admin
    ```

1. Start the scheduled jobs

    Start Worker and Beat:

    ```
    celery -A shadowsocks_manager worker -l info -B
    ```

    Start Worker and Beat with separate processes, this is recommended for production
    deployment:

    ```
    celery -A shadowsocks_manager worker -l info
    celery -A shadowsocks_manager beat -l info
    ```


## Optional Production Deployment

1. Application Server (Optional)

    Running Django application inside an application server such as uWSGI
    instead of using Django built-in server named `runserver` is
    recommended for production deployment.

    Refer to the doc:
    [How to use Django with uWSGI](https://docs.djangoproject.com/en/2.2/howto/deployment/wsgi/uwsgi/).

1. Web Server(Optional):

    Serving static files from a dedicated server such as nginx is recommended for
    production deployment.

    Refer to the doc:
    [Setting up Django and your web server with uWSGI and nginx](https://uwsgi.readthedocs.io/en/latest/tutorials/Django_and_nginx.html)


## Differences from the alternation: [shadowsocks/shadowsocks-manager](https://github.com/shadowsocks/shadowsocks-manager)

* This repo Do's:

    * Serve as a nonprofit business model.
    * Have central user management for multi nodes.
    * Collect traffic statistics which can be viewed by account, node
    and period.
    * Show the existence and accessibility of ports in the admin.
    * Handle the DNS recorders if using Name.com as nameserver.

* This repo Don'ts:

    * Handle self-serviced user registration.
    * Handle bill or payment.
    * Run additional agent on each Shadowsocks server.


## Known Issues

1. DNS records matching for Node may not accurate on macOS.

    For unknown reason sometimes DNS query returns only one IP address
    even multiple IPs were configured for the domain.


## Troubleshooting

1. Check Logs

   uWSGI:

   ```
   cat /var/log/ssm-uwsgi.log
   ```

   Celery:

   ```
   cat /var/log/ssm-cerlery*
   ```

   Supervisor

   ```
   cat /tmp/supervisord.log
   ```

1. Check Services

   Supervisor:

   ```
   service supervisord status
   supervisorctl reload
   supervisorctl start all
   ```

   uWSGI:

   ```
   supervisorctl start ssm-uwsgi
   ```

   Celery:

   ```
   supervisorctl start ssm-celery-worker
   supervisorctl start ssm-celery-beat
   ```

1. Check Ports

   TCP:

   ```
   netstat -tan
   ```

   UDP:

   ```
   netstat -uan
   ```

1. Check Processes

   ```
   ps -ef
   ```


## TODO

* Auto deactivate/activate nodes based on triffic usage and quota.
* Support LDAP.
