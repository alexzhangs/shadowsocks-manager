# -*- coding: utf-8 -*-

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals
from __future__ import absolute_import
from builtins import bytes
from builtins import str
from builtins import range
import six

import sys, os, socket, time, json
import logging
import subprocess, psutil
from subprocess import PIPE
from ipaddress import ip_address
from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _
from django_enumfield import enum
import boto3

from retry import retry
from singleton.models import SingletonModel
from dynamicmethod.models import DynamicMethodModel
from notification.models import Template, Notify
from domain.models import Record


logger = logging.getLogger('django')


# Create your models here.

class Config(SingletonModel):
    port_begin = models.PositiveIntegerField('Begin port', default=8381,
        help_text='Port range allowed for all Shadowsocks nodes, make sure they are opened '
            'on both network firewall and host firewall.')
    port_end = models.PositiveIntegerField('End port', default=8480,
        help_text='Port range allowed for all Shadowsocks nodes, make sure they are opened '
            'on both network firewall and host firewall.')
    timeout_remote = models.FloatField('Global Network Timeout', default=3,
        help_text='Time out setting used by the manager internally, for communicating with '
            'remote SS nodes.')
    timeout_local = models.FloatField('Local Network Timeout', default=0.5,
        help_text='Time out setting used by the manager internally, for communicating with '
            'local SS nodes.')
    cache_timeout = models.IntegerField('Cache Timeout', default=300,
        help_text='Timeout for the cache of the manger API and the Shadowsocks port accessibility.')
    dt_created = models.DateTimeField('Created', auto_now_add=True)
    dt_updated = models.DateTimeField('Updated', auto_now=True)

    class Meta:
        verbose_name = 'Shadowsocks Configuration'


class StatisticMethod(models.Model, DynamicMethodModel):

    ## each '%s' within <template> will be replaced with the value of <variables> ##
    dynamic_methods = [{
        'template': '''

def dynamic_method_template(self):
    from statistic.models import Statistic, Period
    period = Period.objects.filter(year=None, month=None).first()
    kwargs = {
        self.__class__.__name__.lower(): self,
        "period": period
    }
    try:
        return Statistic.objects.get(**kwargs).%s
    except Statistic.DoesNotExist: pass
    except Statistic.MultipleObjectsReturned: pass

''',

        'method': {
            'transferred_past': {
                'variables': ['transferred_past'],
                'property': True
            },
            'transferred_live': {
                'variables': ['transferred_live'],
                'property': True
            },
            'transferred_totally': {
                'variables': ['transferred'],
                'property': True
            },
            'dt_collected': {
                'variables': ['dt_collected'],
                'property': True
            }
        }
    }]

    class Meta:
        abstract = True


class Account(User, StatisticMethod):
    statistic = GenericRelation('statistic.Statistic', related_query_name='account')
    dt_updated = models.DateTimeField('Updated', auto_now=True)

    class Meta:
        verbose_name = 'Shadowsocks Account'

    def __init__(self, *args, **kwargs):
        super(Account, self).__init__(*args, **kwargs)
        self._original_username = self.username
        self._original_password = self.password
        self._original_is_active = self.is_active

    def __str__(self):
        return '%s (%s)' % (self.get_username(), self.get_full_name())

    def clean(self):
        config = Config.load()
        if int(self.username) not in list(range(config.port_begin, config.port_end + 1)):
            raise ValidationError(_('Port number must be in the range of Config: '
                'port_begin(%s) and port_end(%s)' % (config.port_begin, config.port_end)))

    def save(self, *args, **kwargs):
        ret = super(Account, self).save(*args, **kwargs)

        # set a default group
        obj = Group.objects.get(name='shadowsocks-clients')
        if obj not in self.groups.all():
            self.groups.add(obj)

        return ret

    def notify(self, sender=None):
        """
        Send account owner the account information by email.
        """
        if not self.email:
            raise ValidationError({'email': ["There's no Email address configured for %s." % self.get_full_name()]})

        if not self.is_active:
            raise ValidationError({'is_active': ["Skipped sending account Email to %s(%s), beacause the user is "
                "inactive." % (self.email, self.get_full_name)]})

        nas = self.nodes_ref.filter(is_active=True)
        if not nas:
            raise ValidationError("Skipped sending account Email to %s(%s), there's no active node "
                "assigned." % (self.email, self.get_full_name()))

        template = Template.objects.get(type='account_created')

        kwargs = {'account': self, 'node_accounts': []}
        for na in nas:
            d = {}
            kwargs['node_accounts'].append(d)
            d['node'] = na.node
            d['account'] = na.account
        kwargs['sender'] = sender

        message = template.render(kwargs)

        logger.info("Sending VPN account Email to %s(%s) on port %s" % (self.email, \
            self.get_full_name(), self.username))
        return Notify.sendmail(message, sender.get_full_name(), sender.email)

    def on_update(self):
        for na in self.nodes_ref.all():
            if self._original_username != self.username: # port is changed
                na.on_delete(original=True)
                na.on_update()
            elif self._original_password != self.password: # password is changed
                na.on_delete()
                na.on_update()
            if self._original_is_active != self.is_active: # activity is changed
                new = (self.is_active and na.node.is_active)
                if na.is_active != new:
                    na.is_active = new
                    na.save()

    def toggle_active(self):
        self.is_active = not self.is_active
        self.save()

    def add_all_nodes(self):
        nodes = []
        for node in Node.objects.all():
            if NodeAccount.objects.filter(node=node, account=self).count() == 0:
                na = NodeAccount(node=node, account=self, is_active=(self.is_active and node.is_active))
                na.save()
                nodes.append(node)
        return nodes


class Node(StatisticMethod):
    name = models.CharField(unique=True, max_length=32, help_text='Give the node a name.')
    record = models.ForeignKey(Record, null=True, blank=True, on_delete=models.SET_NULL, related_name='nodes',
        help_text='Domain name resolved to the node public IP.')
    public_ip = models.GenericIPAddressField('Public IP', protocol='both', unpack_ipv4=True,
        unique=True, null=True, blank=True, help_text='Public IP address for the node.')
    private_ip = models.GenericIPAddressField('Private IP', protocol='both', unpack_ipv4=True,
        null=True, blank=True, help_text='Private IP address for the node.')
    location = models.CharField(max_length=64, null=True, blank=True,
        help_text='Geography location for the node, appears in the account notification '
            'Email if not blank, example: Hongkong.')
    is_active = models.BooleanField(default=True, help_text='Is this node ready to be online')
    sns_endpoint = models.CharField(max_length=128, null=True, blank=True,
        help_text='AWS SNS Arn which is used to send messages to manage this node(the feature of aws-cfn-vpn).')
    sns_access_key = models.CharField(max_length=128, null=True, blank=True,
        help_text='AWS Access Key ID used to publish SNS messages.')
    sns_secret_key = models.CharField(max_length=128, null=True, blank=True,
        help_text='AWS Secret Access Key used to publish SNS messages.')
    statistic = GenericRelation('statistic.Statistic', related_query_name='node')
    dt_created = models.DateTimeField('Created', auto_now_add=True)
    dt_updated = models.DateTimeField('Updated', auto_now=True)

    class Meta:
        verbose_name = 'Shadowsocks Node'

    def __init__(self, *args, **kwargs):
        super(Node, self).__init__(*args, **kwargs)
        self._original_is_active = self.is_active
        self._original_public_ip = self.public_ip

    def __str__(self):
        return self.name

    def clean(self):
        if not (self.record or self.public_ip):
            raise ValidationError(_('%s: Require to input at least one field: record and '
                'public_ip.' % self))

    @property
    def sns_endpoint_region(self):
        """
        Return the region in the SNS topic endpoint.
        """
        try:
            return self.sns_endpoint.split(':')[3]
        except AttributeError:
            raise ValidationError({'sns_endpoint': [_('The SNS topic endpoint was not configured.')]})
        except IndexError:
            raise ValidationError({'sns_endpoint': [_('The SNS topic endpoint is not a valid ARN.')]})

    @property
    def ssmanager(self):
        return self.ssmanagers.first()

    @classmethod
    def is_port_open(cls, ip, port):
        """
        Test if a TCP port is listening on the IP.
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # TCP

        try:
            if ip_address(ip).is_private:
                s.settimeout(Config.load().timeout_local) # seconds
            else:
                s.settimeout(Config.load().timeout_remote) # seconds
            s.connect((ip, int(port)))
            s.shutdown(socket.SHUT_RDWR)
            return True
        except:
            return False
        finally:
            s.close()

    @property
    def is_matching_dns_query(self):
        """
        Test if the the node.public_ip matches the DNS query.
        """
        if self.record:
            return self.public_ip in self.record.answer_from_dns_query

    @property
    def is_matching_record(self):
        """
        Test if the the node.related_public_ips matches the node.record.answser.
        """
        if self.record:
            return self.related_public_ips() == self.record.answers

    def update_record(self):
        """
        Update the node.record's answer to be the node's related_public_ips.
        """
        if self.record:
            self.record.answer = ",".join(self.related_public_ips())
            self.record.save()

    def related_public_ips(self, is_active=True):
        """
        Return a set of public IP addresses on nodes(including this node) that share the same record
        with this node.
        """
        nodes = self.record.nodes.all() if self.record else [self]
        return {
            node.public_ip
            for node in nodes
            if node.is_active == is_active and node.public_ip
        }

    def get_ip_field_by_interface(self, interface):
        return '{}_ip'.format(InterfaceList.name(interface).lower())

    def get_ip_by_interface(self, interface):
        """
        Return the node's IP address for a network interface.
        """
        if interface == InterfaceList.LOCALHOST:
            return '127.0.0.1'
        else:
            return getattr(self, self.get_ip_field_by_interface(interface))

    def is_port_accessible(self, port):
        """
        Test if a TCP port is listening on the public IP address of this node.
        """
        return Node.is_port_open(self.public_ip, port)

    def clear_cache(self):
        pass

    def on_update(self):
        # changes on public_ip or private_ip need to restart ssmanager
        if self.ssmanager:
            self.ssmanager.on_update()

        for na in self.accounts_ref.all():
            if self._original_is_active != self.is_active: # activity is changed
                new = (self.is_active and na.account.is_active)
                if na.is_active != new:
                    na.is_active = new
                    na.save()

        if not self.is_matching_record:
            self.update_record()

    def toggle_active(self):
        self.is_active = not self.is_active
        self.save()

    def change_ip(self):
        """
        Send a SNS message to trigger the replacement of the node IP in remote AWS.
        This is a feature of [aws-cfn-vpn](https://github.com/alexzhangs/aws-cfn-vpn).
        """
        sns = boto3.resource(
            'sns',
            region_name=self.sns_endpoint_region,
            aws_access_key_id=self.sns_access_key,
            aws_secret_access_key=self.sns_secret_key
        )
        topic = sns.Topic(self.sns_endpoint)
        return topic.publish(Message='change_ip')

    @classmethod
    def change_ips(cls):
        """
        Replace the IPs of all the active nodes in remote AWS.
        This is a feature of [aws-cfn-vpn](https://github.com/alexzhangs/aws-cfn-vpn).
        """
        for node in cls.objects.filter(
            is_active=True,
            sns_endpoint__isnull=False,
            sns_access_key__isnull=False,
            sns_secret_key__isnull=False,
        ):
            node.change_ip()

    @classmethod
    def change_ips_softly(cls):
        """
        Softly replace the IPs of all the active nodes in remote AWS.
        The following steps are taken for the nodes one by one, to avoid the service outage for clients:
          1. Inactivate the node to remove the node IP from the DNS record list.
          2. Sleep 5 minutes to wait for the DNS record take effect.
          3. Send a message to trigger the IP replacement.
          4. Sleep 1 minutes to wait for the AWS config to capture the new IP, and send it back to django.
          5. Activate the node to add the new node IP to the DNS record list.
        The whole process takes around 10 minutes for each node to take effect on client side.
        Updating DNS record on the fly is depends on the NameServer API which you have to set first in the domain app.
        This is a feature of [aws-cfn-vpn](https://github.com/alexzhangs/aws-cfn-vpn).
        """
        for node in cls.objects.filter(
            is_active=True,
            sns_endpoint__isnull=False,
            sns_access_key__isnull=False,
            sns_secret_key__isnull=False,
        ):
            node.toggle_active()  # make the node inactive
            time.sleep(300)  # assuming your DNS record TTL is 300 seconds
            node.change_ip()
            time.sleep(60)  # AWS config capture takes time
            node.toggle_active()  # make the node active again


class NodeAccount(StatisticMethod):
    node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name='accounts_ref')
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='nodes_ref')
    statistic = GenericRelation('statistic.Statistic', related_query_name='nodeaccount')
    is_active = models.BooleanField(default=True, help_text='Creating account on this node?')
    dt_created = models.DateTimeField('Created', auto_now_add=True)
    dt_updated = models.DateTimeField('Updated', auto_now=True)

    class Meta:
        verbose_name = 'Shadowsocks Node to Account'
        unique_together = ('node', 'account')

    def __str__(self):
        return '%s on %s' % (self.account, self.node)

    def is_created(self, original=False):
        """
        Test if the port is created on the node using Manager API: ping.
        """
        if not self.node.ssmanager:
            return

        if original:
            return self.node.ssmanager.is_port_created(self.account._original_username)
        else:
            return self.node.ssmanager.is_port_created(self.account.username)

    is_created.boolean = True

    @property
    def is_accessible(self):
        """
        Test if the TCP port is listening on the public IP of the node.
        """
        return self.node.is_port_accessible(self.account.username)

    def is_accessible_ex(self, from_cache=True):
        """
        The same as is_accessible, but with cache enabled.
        The cache lives for 60 seconds.
        """
        key, value = ('{0}:{1}'.format(self.node.public_ip, self.account.username), None)
        if from_cache and key in cache:
            logger.debug('hitting cache: %s' % key)
            value = cache.get(key)
        else:
            value = self.is_accessible
            cache.set(key, '' if value is None else value, timeout=Config.load().cache_timeout)

        return value

    def clear_cache(self):
        """
        Clear all the cache made by this instance:
        * is_accessible_ex()
        """
        key = '{0}:{1}'.format(self.node.public_ip, self.account.username)
        logger.debug('clearing cache: %s' % key)
        cache.delete(key)

    @classmethod
    def clear_caches(cls, node=None, account=None):
        """
        Clear all the cache made by this class by filters:
        * node
        * account
        """
        objs = cls.objects.all()
        if node: objs = objs.filter(node=node)
        if account: objs = objs.filter(account=account)
        keys = ['{0}:{1}'.format(obj.node.public_ip, obj.account.username) for obj in objs]
        logger.debug('clearing caches: %s' % keys)
        cache.delete_many(keys)

    def on_update(self):
        if not self.node.ssmanager:
            return

        if self.is_active:
            if self.node.ssmanager.is_accessible:
                self.node.ssmanager.add(port=self.account.username, password=self.account.password)
                self.clear_cache()
            else:
                logger.error('%s: creation eror: ssmanager %s currently is not available.' \
                    % (self, self.node.ssmanager))
        else:
            self.on_delete()

    def on_delete(self, original=False):
        if not self.node.ssmanager:
            return

        port = '_original_username' if original else 'username'
        if self.node.ssmanager.is_accessible:
            self.node.ssmanager.remove(port=getattr(self.account, port))
            self.clear_cache()
        else:
            logger.error('%s: deletion eror: ssmanager %s currently is not available.' % (self, \
                self.node.ssmanager))

    @classmethod
    def heartbeat(cls):
        """
        Heartbeat once on all the nodeaccounts.
        Create the active ones and delete the inactive ones on the corresponding nodes.
        This method usually is used to run as the scheduled job.
        """
        for na in cls.objects.all():
            na.on_update()


class InterfaceList(enum.Enum):
    LOCALHOST = 1
    PRIVATE = 2
    PUBLIC = 3

    __labels__ = {
        LOCALHOST: "Localhost",
        PRIVATE: "Private",
        PUBLIC: "Public"
    }


class ServerEditionList(enum.Enum):
    LIBEV = 1
    PYTHON = 2

    __labels__ = {
        LIBEV: "libev",
        PYTHON: "python",
    }


class SSManager(models.Model):
    node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name='ssmanagers')
    interface = enum.EnumField(InterfaceList, default=InterfaceList.LOCALHOST,
        help_text='Network interface bound to Manager API on the node, use an internal '
            'interface if possible.')
    port = models.PositiveIntegerField(default=6001,
        help_text='Port number bound to Manager API.')
    encrypt = models.CharField(max_length=32, default='aes-256-cfb',
        help_text='Encrypt method: rc4-md5, aes-128-gcm, aes-192-gcm, aes-256-gcm, '
        'aes-128-cfb, aes-192-cfb, aes-256-cfb, aes-128-ctr, aes-192-ctr, aes-256-ctr, '
        'camellia-128-cfb, camellia-192-cfb, camellia-256-cfb, bf-cfb, chacha20-ietf-poly1305, '
        'xchacha20-ietf-poly1305, salsa20, chacha20 and chacha20-ietf.')
    timeout = models.PositiveIntegerField(default=30,
        help_text='Socket timeout in seconds for Shadowsocks client.')
    fastopen = models.BooleanField('Fast Open', default=False,
        help_text='Enable TCP fast open, with Linux kernel > 3.7.0.')
    server_edition = enum.EnumField(ServerEditionList, default=ServerEditionList.LIBEV,
        help_text='The Shadowsocks server edition. The libev edition is recommended.')
    is_v2ray_enabled = models.BooleanField(default=False,
        help_text='Whether the v2ray-plugin is enabled for Shadowsocks server. The changes made here will not '
            'affect the plugin status on server.')
    is_server_enabled = models.BooleanField(default=False,
        help_text='Control the Shadowsocks server up or down. Works only with the Shadowsocks python edition '
            'local node.')
    dt_created = models.DateTimeField('Created', auto_now_add=True)
    dt_updated = models.DateTimeField('Updated', auto_now=True)

    class Meta:
        verbose_name = 'Shadowsocks Manager'

    def __str__(self):
        return '%s:%s' % (self._ip, self.port)

    def __init__(self, *args, **kwargs):
        super(SSManager, self).__init__(*args, **kwargs)
        self._original_port = self.port
        self._original_server_edition = self.server_edition

    def clean(self):
        if not self._ip:
            raise ValidationError({
                self.node.get_ip_field_by_interface(self.interface):
                [_('There is no IP address set for selected interface on the node.')]})
        if self.is_server_enabled and self.server_edition != ServerEditionList.PYTHON:
            raise ValidationError({
                'is_server_enabled':
                [_('is_server_enabled was set without Shadowsocks python edition.')]})

    @property
    def server(self):
        return SSServer(self)

    @property
    def _ip(self):
        """
        Return the node's IP address on the network interface that the Manager API is listening on.
        """
        return self.node.get_ip_by_interface(self.interface)

    def connect(self):
        """
        Open a connection to the Manager API by UDP.
        """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
        if ip_address(self._ip).is_private:
            self.socket.settimeout(Config.load().timeout_local) # seconds
        else:
            self.socket.settimeout(Config.load().timeout_remote) # seconds
        self.socket.connect((self._ip, self.port))

    def close(self):
        """
        Close the connection to the Manager API.
        """
        self.socket.shutdown(socket.SHUT_RDWR)
        self.socket.close()

    def call(self, command, read=False):
        """
        Make a command call to the Manager API.
        """
        ret = None
        if isinstance(command, six.text_type):
            command = bytes(command, 'utf-8')

        self.connect()
        try:
            self.socket.send(command)
            if read:
                ret = self.socket.recv(4096)
                ret = str(ret, 'utf-8')
        except socket.timeout:
            logger.error('%s: %s: timed out in %s seconds' % (self, command, self.socket.gettimeout()))
        except Exception as e:
            logger.error('%s: %s: unexpected error: %s' % (self, command, e))
        finally:
            self.close()

        return ret

    def _add(self, port, password):
        """
        Manager API command: `add: {"server_port": <port>, "password": <password>}`.
        Add a user with password.
        """
        command = 'add: { "server_port": %s, "password": "%s" }' % (port, password)
        self.call(command)

    def _remove(self, port):
        """
        Manager API command: `remove: {"server_port": <port>}`.
        Remove a user.
        """
        command = 'remove: { "server_port": %s }' % port
        self.call(command)

    def _ping(self):
        """
        Manager API command: `ping`.
        * For Shadowsocks libev edition: returns all users: 'stat: {...}'.
        * For Shadowsocks python edition: returns simple string: 'pong'.
        """
        command = 'ping'
        return self.call(command, read=True)

    def _list(self):
        """
        Manager API command: `list`.
        List all users with password.
        Works only for libev edition.
        This is an undocumented Shadowsocks Manager Command, but works.
        """
        if self.server_edition == ServerEditionList.LIBEV:
            command = 'list'
            return self.call(command, read=True)

    @retry(count=1, delay=1, logger=logger)
    def add(self, port, password):
        """
        Add a user with password, return the final user existence status in Boolean.
        Skip if the user already exists.
        Auto-retry enabled.
        """
        exists = self.is_port_created_or_accessible(port)
        if not exists:
            self._add(port, password)
            self.clear_cache()
            self.get_nodeaccount(port, create=True).clear_cache()
            exists = self.is_port_created_or_accessible(port)
        return exists

    @retry(count=1, delay=1, logger=logger)
    def remove(self, port):
        """
        Remove a user, return the final user non-existence status in Boolean.
        Skip if the user doesn't exist.
        Auto-retry enabled.
        """
        exists = self.is_port_created_or_accessible(port)
        if exists:
            self._remove(port)
            self.clear_cache()
            self.get_nodeaccount(port, create=True).clear_cache()
            exists = self.is_port_created_or_accessible(port)
        return not exists

    def ping(self):
        """
        Send ping.
        * for Shadowsocks libev edition: list all users, return in JSON.
        * for Shadowsocks python edition: return a emtpy dict: {}.
        """
        data = self._ping()
        if not data:
            return None
        parts = data.split(':', 1)
        if len(parts) == 2:
            # libev edition
            return json.loads(parts[1])
        else:
            # python edition
            return {}

    def list(self):
        """
        List all users with password, return in JSON.
        Works only for libev edition.
        """
        ports = self._list()
        if ports:
            try:
                return json.loads(ports)
            except ValueError:
                return list()
        else:
            return None

    def clear_cache(self):
        """
        Clear all the cache made by this instance:
        * ping_ex()
        * list_ex()
        """
        keys = ['{0}-{1}'.format(self, str) for str in ['ping', 'list']]
        logger.debug('clearing cache: %s' % keys)
        cache.delete_many(keys)

    def ping_ex(self, from_cache=True):
        """
        The same as ping(), but with cache enabled.
        The cache lives for 60 seconds.
        """
        key, value = ('{0}-{1}'.format(self, 'ping'), None)
        if from_cache and key in cache:
            logger.debug('hitting cache: %s' % key)
            value = cache.get(key)
        else:
            value = self.ping()
            cache.set(key, '' if value is None else value, timeout=Config.load().cache_timeout)

        return value

    def list_ex(self, from_cache=True):
        """
        The same as list(), but with cache enabled.
        The cache lives for 60 seconds.
        """
        key, value = ('{0}-{1}'.format(self, 'list'), None)
        if from_cache and key in cache:
            logger.debug('hitting cache: %s' % key)
            value = cache.get(key)
        else:
            value = self.list()
            cache.set(key, '' if value is None else value, timeout=Config.load().cache_timeout)

        return value

    def is_port_created(self, port):
        """
        Test if a port is created with Manager API.
        Internally using list_ex().
        """
        items = self.list_ex()
        if isinstance(items, list):
            return any(item['server_port'] == str(port) for item in items)
        else:
            return None

    def is_port_created_or_accessible(self, port):
        """
        Test if a port is created with Manager API.
        Internally using list_ex().
        If the Manager API is not available or not accessible, then test the port accessibility directly.
        """
        ret = self.is_port_created(port)
        return self.get_nodeaccount(port, create=True).is_accessible_ex() if ret is None else ret

    def get_nodeaccount(self, port, create=False):
        try:
            account = Account.objects.get(username=port)
            return NodeAccount.objects.get(node=self.node, account=account)
        except (Account.DoesNotExist, NodeAccount.DoesNotExist):
            if create:
                return NodeAccount(node=self.node, account=Account(username=port))
            else:
                raise

    @property
    def is_accessible(self):
        """
        Test if the manager is in service.
        Internally using ping_ex().
        """
        return self.ping_ex() is not None

    def on_update(self):
        if self.server_edition != self._original_server_edition and self._original_server_edition == ServerEditionList.PYTHON:
            self.server.stop()
            self.clear_cache()
            NodeAccount.clear_caches(node=self.node)
        if self.server_edition == ServerEditionList.PYTHON:
            if self.is_server_enabled:
                self.server.restart()
            else:
                self.server.stop()
            self.clear_cache()
            NodeAccount.clear_caches(node=self.node)

    def on_delete(self):
        self.server.stop()
        self.clear_cache()
        NodeAccount.clear_caches(node=self.node)


class SSServer(object):

    def __init__(self, manager, *args, **kwargs):
        super(SSServer, self).__init__(*args, **kwargs)
        self.manager = manager
        # the lift_pip_shadowsocks is no longer needed after the django app shadowsocks was renamed to shadowsocksz
        # self.lift_pip_shadowsocks()

    def pidfile(self, original=False):
        return '/tmp/shadowsocks-{}.pid'.format(self.manager._original_port if original else self.manager.port)

    def logfile(self, original=False):
        return '/tmp/shadowsocks-{}.log'.format(self.manager._original_port if original else self.manager.port)

    @classmethod
    def lift_pip_shadowsocks(cls):
        """
        Workaround for the package naming conflict between the Django app `shadowsocks` and the pip package `shadowsocks`.
        Lower the searching priority of the Django project app home dir in sys.path.
        """
        import shadowsocks
        # get the package's path
        p = shadowsocks.__path__[0]
        if not p.endswith('/shadowsocks_manager/shadowsocks'):
            # shadowsocks is not referring to the Django app, nothing to do
            return

        # remove last item from path
        p = '/'.join(p.split('/')[0:-1])

        # due with sys.path, for current environment
        flag = None
        while sys.path.count(p) > 0:
            sys.path.remove(p)
            flag = True
        if flag:
            # add the Django project app home dir back to the end
            sys.path.append(p)

        # due with PYTHONPATH, for subprocess
        pythonpath = (os.getenv('PYTHONPATH') or '').split(':')
        flag = None
        while pythonpath.count(p) > 0:
            pythonpath.remove(p)
            flag = True

        if flag:
            # add the Django project app home dir back to the end
            os.putenv('PYTHONPATH', ':'.join(pythonpath + sys.path + [p]))

        # unimport the package
        del sys.modules['shadowsocks']

    def call(self, command, *args, **kwargs):
        """
        Call Shadowsocks server command by subprocess.Popen().
        Return (exit_code, stdout, stderr)
        """
        proc = subprocess.Popen(command, *args, stdout=PIPE, stderr=PIPE,
                                **kwargs)
        (stdout, stderr) = proc.communicate()
        rc = proc.wait()
        return (rc, str(stdout, 'utf-8'), str(stderr, 'utf-8'))

    @property
    def version(self):
        """
        Return the installed Shadowsocks version.
        """
        if self.manager.server_edition == ServerEditionList.LIBEV:
            command = ['ss-manager', '-h']
        elif self.manager.server_edition == ServerEditionList.PYTHON:
            command = ['ssserver', '--version']

        try:
            (rc, stdout, stderr) = self.call(command)
            if rc == 0:
                return stdout.split(' ')[1].strip('\n')
        except OSError:
            pass

    @property
    def status(self):
        """
        Return the Shadowsocks process's pid and status.
        """
        try:
            with open(self.pidfile(), 'r') as f:
                pid = int(f.read())
            p = psutil.Process(pid=pid).as_dict(['pid', 'status'])
            return '{status}({pid})'.format(**p)
        except:
            pass

    '''
    def install(self):
        """
        Install Shadowsocks python edition.
        Skip if already installed.
        """
        if not self.version:
            command = ['pip', 'install', 'shadowsocks']
            (rc, stdout, stderr) = trace_call(command)
            if rc != 0:
                raise Exception(stderr)

    def uninstall(self):
        """
        Uninstall Shadowsocks python edition.
        Skip if not installed.
        """
        if self.version:
            command = ['pip', 'uninstall', '-y', 'shadowsocks']
            (rc, stdout, stderr) = trace_call(command)
            if rc != 0:
                raise Exception(stderr)
    '''

    def start(self):
        """
        Start the Shadowsocks server with manager.
        """
        command = [
            'ssserver',
            '--pid-file', self.pidfile(),
            '--log-file', self.logfile(),
            '-d', 'start',
            '--manager-address', '{}:{}'.format(self.manager._ip, self.manager.port),  # the options order matters
            '-k', 'passw0rd',
            '-m', self.manager.encrypt,
            '-t', str(self.manager.timeout),
            '--fast-open', str(self.manager.fastopen),
        ]
        """
        * close_fds=True: For Python 2.7, should not inherit the parent process's fds. The inherit fds won't be released
                          after the parent process was exited but the child process remains.
                          Here's the Django server's process that's bound with a port.
        """
        (rc, stdout, stderr) = self.call(command, close_fds=True)
        if rc == 0:
            logger.debug(stdout)
        else:
            logger.error('stderr: %s\nstdout: %s' % (stderr, stdout))

    def stop(self):
        """
        Stop the Shadowsocks server.
        """
        command = [
            'ssserver',
            '--pid-file', self.pidfile(original=True),
            '--log-file', self.logfile(original=True),
            '-d', 'stop',
        ]
        (rc, stdout, stderr) = self.call(command)
        if rc == 0:
            logger.debug(stdout)
        else:
            logger.error('stderr: %s\nstdout: %s' % (stderr, stdout))

    def restart(self):
        """
        Restart the Shadowsocks server.
        """
        self.stop()
        self.start()


@receiver(post_save, sender=NodeAccount)
def update_account_on_node(sender, instance, **kwargs):
    instance.on_update()


@receiver(post_delete, sender=NodeAccount)
def delete_account_on_node(sender, instance, **kwargs):
    instance.on_delete()


@receiver(post_save, sender=Account)
def update_by_account(sender, instance, **kwargs):
    instance.on_update()


@receiver(post_save, sender=Node)
def update_by_node(sender, instance, **kwargs):
    instance.on_update()


@receiver(post_save, sender=SSManager)
def update_ssmanager(sender, instance, **kwargs):
    instance.on_update()


@receiver(post_delete, sender=SSManager)
def delete_ssmanager(sender, instance, **kwargs):
    instance.on_delete()
