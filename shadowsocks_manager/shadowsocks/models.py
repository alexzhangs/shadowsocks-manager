# -*- coding: utf-8 -*-

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals
from builtins import bytes
from builtins import str
from builtins import range
import six

import socket, time, json
import logging
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
    timeout = models.PositiveIntegerField('Network Timeout', default=5,
        help_text='Time out setting used by the manager internally, for communicating with '
            'SS nodes.')
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
    period = Period.objects.get(year=None, month=None)
    kwargs = {
        self.__class__.__name__.lower(): self,
        "period": period
    }
    return Statistic.objects.get(**kwargs).%s

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
        if not self.email:
            logger.error("There's no Email address configured for %s." % self.get_full_name())
            return False

        if not self.is_active:
            logger.warning("Skipped sending account Email to %s(%s), beacause the user is "
                "inactive." % (self.email, self.get_full_name))
            return False

        nas = self.nodes_ref.filter(is_active=True)
        if not nas:
            logger.warning("Skipped sending account Email to %s(%s), there's no active node "
                "assigned." % (self.email, self.get_full_name()))
            return False

        template = Template.objects.get(type='account_created')

        kwargs = {}
        kwargs['account'] = self
        kwargs['node_accounts'] = []
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
            elif self._original_password != self.password: # password is changed
                na.on_delete()
            else:
                pass

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
        help_text='AWS SNS Arn which is used to send messages to manage this node.')
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
    def ssmanager(self):
        ssmanagers = self.ssmanagers.all()
        if ssmanagers:
            return ssmanagers[0]

    @classmethod
    def is_port_open(cls, ip, port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # TCP

        try:
            s.settimeout(Config.load().timeout) # seconds
            s.connect((ip, int(port)))
            s.shutdown(socket.SHUT_RDWR)
            return True
        except:
            return False

    # test if dns records match the public IP
    @property
    def is_matching_dns_query(self):
        if self.record:
            return self.public_ip in (self.record.answer_from_dns_query or [])

    def get_ip_by_interface(self, interface):
        if interface == InterfaceList.LOCALHOST:
            return '127.0.0.1'
        else:
            return getattr(self, '{}_ip'.format(InterfaceList.name(interface).lower()))

    # test if a port is open
    def is_port_accessible(self, port):
        return Node.is_port_open(self.public_ip, port)

    def on_update(self):
        for na in self.accounts_ref.all():
            if self._original_is_active != self.is_active: # activity is changed
                new = (self.is_active and na.account.is_active)
                if na.is_active != new:
                    na.is_active = new
                    na.save()

        if self.record and (self._original_is_active != self.is_active or self._original_public_ip != self.public_ip):
            self.record.answer = ",".join([node.public_ip for node in self.record.nodes.all() if node.is_active and node.public_ip])
            self.record.save()

    def toggle_active(self):
        self.is_active = not self.is_active
        self.save()

    def change_ip(self):
        if self.sns_endpoint:
            sns = boto3.resource(
                'sns',
                region_name=self.sns_endpoint.split(':')[3],
                aws_access_key_id=self.sns_access_key,
                aws_secret_access_key=self.sns_secret_key
            )
            topic = sns.Topic(self.sns_endpoint)
            return topic.publish(
                Message='change_ip'
            )

    @classmethod
    def change_ips(cls):
        for node in cls.objects.filter(is_active=True):
            node.change_ip()

    @classmethod
    def change_ips_softly(cls):
        for node in cls.objects.filter(is_active=True):
            node.toggle_active()
            node.change_ip()
            # it takes around 20 minutes to capture the change and let the
            # updated DNS records take effect.
            time.sleep(1200)
            node.toggle_active()


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

    # test with Manager API ping
    def is_created(self, original=False):
        if original:
            return self.node.ssmanager.is_port_created(self.account._original_username)
        else:
            return self.node.ssmanager.is_port_created(self.account.username)

    is_created.boolean = True

    # test if the port is connectable
    @property
    def is_accessible(self):
        return self.node.is_port_accessible(self.account.username)

    def on_update(self):
        if self.is_active:
            if self.node.ssmanager.is_accessible:
                self.node.ssmanager.add(port=self.account.username, password=self.account.password)
            else:
                logger.error('%s: creation eror: ssmanager %s currently is not available.' \
                    % (self, self.node.ssmanager))
        else:
            self.on_delete()

    def on_delete(self, original=False):
        if original:
            port = '_original_username'
        else:
            port = 'username'

        if self.node.ssmanager.is_accessible:
            self.node.ssmanager.remove(port=getattr(self.account, port))
        else:
            logger.error('%s: deletion eror: ssmanager %s currently is not available.' % (self, \
                self.node.ssmanager))

    @classmethod
    def heartbeat(cls):
        for na in cls.objects.filter(is_active=True):
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


class SSManager(models.Model):
    node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name='ssmanagers')
    interface = enum.EnumField(InterfaceList, default=InterfaceList.LOCALHOST,
        help_text='Network interface bound to Manager API on the node, use an internal '
            'interface if possible.')
    port = models.PositiveIntegerField(default=6001,
        help_text='Port number bound to Manager API.')
    encrypt = models.CharField(max_length=32, default='aes-256-cfb',
        help_text='Encrypt method: rc4-md5, aes-128-gcm, aes-192-gcm, aes-256-gcm,'
        'aes-128-cfb, aes-192-cfb, aes-256-cfb, aes-128-ctr, aes-192-ctr, aes-256-ctr, '
        'camellia-128-cfb, camellia-192-cfb, camellia-256-cfb, bf-cfb, chacha20-ietf-poly1305, '
        'xchacha20-ietf-poly1305, salsa20, chacha20 and chacha20-ietf.')
    timeout = models.PositiveIntegerField(default=30,
        help_text='Socket timeout in seconds for Shadowsocks client.')
    fastopen = models.BooleanField('Fast Open', default=False,
        help_text='Enable TCP fast open, with Linux kernel > 3.7.0.')
    dt_created = models.DateTimeField('Created', auto_now_add=True)
    dt_updated = models.DateTimeField('Updated', auto_now=True)

    class Meta:
        verbose_name = 'Shadowsocks Manager'

    def __str__(self):
        return '%s:%s' % (self._ip, self.port)

    def clean(self):
        if not self._ip:
            raise ValidationError(_('There is no IP address set for selected interface on the node.'))

    @property
    def _ip(self):
        return self.node.get_ip_by_interface(self.interface)

    def connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
        self.socket.connect((self._ip, self.port))

    def close(self):
        self.socket.close()

    def call(self, command, read=False):
        ret = None
        if isinstance(command, six.text_type):
            command = bytes(command, 'utf-8')

        self.connect()
        try:
            self.socket.send(command)
            if read:
                self.socket.settimeout(Config.load().timeout)
                ret = self.socket.recv(4096)
                ret = str(ret, 'utf-8')
        except socket.timeout:
            logger.error('%s: timed out on calling command: %s' % (self, command))
        except Exception as e:
            logger.error('%s: unexpected error: %s' % (self, e))
        finally:
            self.close()

        return ret

    def _add(self, port, password):
        command = 'add: { "server_port": %s, "password": "%s" }' % (port, password)
        self.call(command)

    def _remove(self, port):
        command = 'remove: { "server_port": %s }' % port
        self.call(command)

    def _ping(self):
        command = "ping"
        return self.call(command, read=True)

    # Undocumented Shadowsocks Manager Command, but works
    # List all users with password
    def _list(self):
        command = 'list'
        return self.call(command, read=True)

    @retry(count=5, delay=1, logger=logger, level='warning')
    def add(self, port, password):
        exists = self.is_port_created(port)
        if not exists:
            self._add(port, password)
            self.clear_cache()
            exists = self.is_port_created(port)
        return exists

    @retry(count=5, delay=1, logger=logger, level='warning')
    def remove(self, port):
        exists = self.is_port_created(port)
        if exists:
            self._remove(port)
            self.clear_cache()
            exists = self.is_port_created(port)
        return not exists

    def ping(self):
        stat = self._ping()
        if stat:
            return json.loads(stat.lstrip('stat: '))
        else:
            return None

    def list(self):
        ports = self._list()
        if ports:
            try:
                return json.loads(ports)
            except ValueError:
                return list()
        else:
            return None

    def clear_cache(self):
        keys = []
        for str in ['ping', 'list']:
            keys.append('{0}-{1}'.format(self, str))
        cache.delete_many(keys)

    def ping_ex(self, from_cache=True):
        """
        cache 60 seconds
        """
        key, value = ('{0}-{1}'.format(self, 'ping'), None)
        if from_cache and key in cache:
            value = cache.get(key)
        else:
            value = self.ping()
            cache.set(key, value, timeout=60)

        return value

    def list_ex(self, from_cache=True):
        """
        cache 60 seconds
        """
        key, value = ('{0}-{1}'.format(self, 'list'), None)
        if from_cache and key in cache:
            value = cache.get(key)
        else:
            value = self.list()
            cache.set(key, value, timeout=60)

        return value

    # test if a port is created with Manager API
    def is_port_created(self, port):
        items = self.list_ex()
        if items:
            for item in items:
                if item['server_port'] == str(port):
                    return True
        return False

    # test if the manager is in service
    @property
    def is_accessible(self):
        return self.ping_ex() is not None


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
