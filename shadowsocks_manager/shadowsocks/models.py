# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import socket, time, json
import logging
from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from singleton.models import SingletonModel
from dynamicmethod.models import DynamicMethodModel
from notification.models import Config as NConfig, Template, Notify


logger = logging.getLogger('django')


# Create your models here.

class Config(SingletonModel):
    port_begin = models.PositiveIntegerField('Begin port', default=8381, help_text='Port range allowed for all Shadowsocks nodes, make sure they are opened on both network firewall and host firewall.')
    port_end = models.PositiveIntegerField('End port', default=8480, help_text='Port range allowed for all Shadowsocks nodes, make sure they are opened on both network firewall and host firewall.')
    timeout = models.PositiveIntegerField('Network Timeout', default=5, help_text='Time out setting used by the manager internally, for communicating with SS nodes.')
    dt_created = models.DateTimeField('Created', auto_now_add=True)
    dt_updated = models.DateTimeField('Updated', auto_now=True)

    class Meta:
        verbose_name = 'Shadowsocks Configuration'


class Statistics(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    transferred_past = models.PositiveIntegerField('Transferred in Past', default=0)
    transferred_live = models.PositiveIntegerField('Transferred on Living Port', default=0)
    year = models.PositiveIntegerField(null=True, blank=True)
    month = models.PositiveIntegerField(null=True, blank=True)
    dt_collected = models.DateTimeField('Collected', null=True, blank=True)
    dt_created = models.DateTimeField('Created', auto_now_add=True)
    dt_updated = models.DateTimeField('Updated', auto_now=True)

    class Meta:
        verbose_name = 'Statistics'
        verbose_name_plural = verbose_name
        unique_together = ('year', 'month', 'content_type', 'object_id')

    def __unicode__(self):
        return '%s %s %s %s' % (self.content_type.name, self.content_object, self.transferred, self.period)

    @property
    def period(self):
        return str(self.year) + ('-' + str(self.month) if self.month else '') if self.year else None

    @property
    def detailed_period(self):
        return '~'.join([str(self.dt_created.date()), str(self.dt_updated.date())])

    @property
    def transferred(self):
        return self.transferred_past + self.transferred_live

    @property
    def period_type(self):
        if self.year and self.month:
            return 'Monthly'
        elif self.year:
            return 'Yearly'
        elif not (self.year and self.month):
            return 'Overall'
        else:
            logger.error('Unsupported period type: year %s, month %s' % (self.year, self.month))

    @property
    def object_type(self):
        obj_type = self.content_type.model_class().__name__

        if obj_type in ['NodeAccount', 'Node', 'Account']:
            return obj_type
        else:
            logger.error('Unsupported object type: %s' % obj_type)

    @property
    def stat_type(self):
        p = self.period_type
        o = self.object_type
        if p and o:
            return p + o
        else:
            logger.error('Unable to get stat type')

    def update_stat(self, data, timestamp):
        # other than MonthlyNodeAccount, should use 'consolidate_stat'
        assert(self.stat_type == 'MonthlyNodeAccount')

        transferred_live = data.get(self.content_object.account.username, 0)
        if transferred_live < self.transferred_live:
            # changing active/inactive status or restarting server clears the statistics
            self.transferred_past += self.trasferred_live
        else:
            pass

        self.transferred_live = transferred_live
        self.dt_collected = timestamp
        self.save()

    @property
    def consolidate_policy(self):
        policy = {
            'MonthlyNodeAccount': {
                'YearlyNodeAccount': {
                    'OverallNodeAccount': None
                },
                'MonthlyNode': {
                    'YearlyNode': {
                        'OverallNode': None
                    }
                },
                'MonthlyAccount': {
                    'YearlyAccount': {
                        'OverallAccount': None
                    }
                }
            }
        }

        return policy

    def consolidate_filter(self):
        pass

    def consolidate_stat(self):
        # MonthlyNodeAccount should use 'update_stat'
        assert(self.stat_type != 'MonthlyNodeAccount')

        timestamp = None
        transferred_past = 0
        transferred_live = 0

        mstat = self.__class__.objects.filter(**self.consolidate_filter)

        for obj in mstat:
            transferred_past += obj.transferred_past
            transferred_live += obj.transferred_live
            timestamp = obj.dt_collected if obj.dt_collected > timestamp else timestamp

        self.transferred_past = transferred_past
        self.transferred_live = transferred_live
        self.dt_collected = timestamp
        self.save()


class StatisticsMethod(models.Model, DynamicMethodModel):

    ## each '%s' within <template> will be replaced with the value of <variables> ##
    dynamic_methods = [{
        'template': '''

def dynamic_method_template(self):
    import statistics
    kwargs = {
        self.__class__.__name__.lower(): self,
        "period": None
    }
    return statistics.models.Statistics.objects.get(**kwargs).%s

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
            'transferred': {
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


class Account(User, StatisticsMethod):
    statistics = GenericRelation(Statistics, related_query_name='account')
    dt_updated = models.DateTimeField('Updated', auto_now=True)

    class Meta:
        verbose_name = 'Shadowsocks Account'

    def __init__(self, *args, **kwargs):
        super(Account, self).__init__(*args, **kwargs)
        self._original_username = self.username
        self._original_password = self.password

    def __unicode__(self):
        return '%s (%s)' % (self.get_username(), self.get_full_name())

    def save(self, *args, **kwargs):
        ret = super(Account, self).save(*args, **kwargs)

        # set a default group
        obj = Group.objects.get(name='shadowsocks-clients')
        if obj not in self.groups.all():
            self.groups.add(obj)

        return ret

    def notify(self):
        if not self.email:
            logger.error("There's no Email address configured for %s." % self.get_full_name())
            return False

        if not self.is_active:
            logger.warning("Skipped sending account Email to %s(%s), beacause the user is inactive." % (self.email, self.get_full_name))
            return False

        nas = self.nodes_ref.filter(node__is_active=True)
        if not nas:
            logger.warning("Skipped sending account Email to %s(%s), there's no active node assigned." % (self.email, self.get_full_name()))
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
        kwargs['config'] = NConfig.load()

        message = template.render(kwargs)

        logger.info("Sending VPN account Email to %s(%s) on port %s" % (self.email, self.get_full_name(), self.username))
        return Notify.sendmail(message)

    def on_update(self):
        for na in self.nodes_ref.all():

            ## deletion stage

            # if port is changed
            if self._original_username != self.username:
                # call on_delete() to handle deletion logic instead of a truely deletion
                na.on_delete(original=True)

            # if password is changed
            elif self._original_password != self.password or not self.is_active:
                # call on_delete() to handle deletion logic instead of a truely deletion
                na.on_delete()

            else:
                pass

            ## creation stage

            if self.is_active:
                # call on_create() to handle creation logic instead of a truely creation
                na.on_create()
            else:
                pass

    def toggle_active(self):
        self.is_active = not self.is_active
        self.save()


class Node(StatisticsMethod):
    name = models.CharField(unique=True, max_length=32, help_text='Give the node a name.')
    public_ip = models.GenericIPAddressField('Public IP', protocol='both', unpack_ipv4=True, unique=True, help_text='Public IP address for Shadowsocks clients.')
    manager_ip = models.GenericIPAddressField(protocol='both', unpack_ipv4=True, unique=True, null=True, blank=True, help_text='IP address bound to Manager API, use an internal IP if possible, leave it blank if the same with public IP address.')
    manager_port = models.PositiveIntegerField(default=6001, help_text='Port number bound to Manager API.')
    encrypt = models.CharField(max_length=32, default='aes-256-cfb', help_text='Encrypt method: rc4-md5,\
        aes-128-gcm, aes-192-gcm, aes-256-gcm,\
        aes-128-cfb, aes-192-cfb, aes-256-cfb,\
        aes-128-ctr, aes-192-ctr, aes-256-ctr,\
        camellia-128-cfb, camellia-192-cfb,\
        camellia-256-cfb, bf-cfb,\
        chacha20-ietf-poly1305,\
        xchacha20-ietf-poly1305,\
        salsa20, chacha20 and chacha20-ietf.')
    timeout = models.PositiveIntegerField(default=30, help_text='Socket timeout in seconds for Shadowsocks client.')
    fastopen = models.BooleanField('Fast Open', default=False, help_text='Enable TCP fast open, with Linux kernel > 3.7.0.')
    domain = models.CharField(max_length=64, null=True, blank=True, help_text='Domain name resolved to the node IP, appears in the account notification Email, if leave blank, the public IP address for the node will be used, example: shadowsocks.yourdomain.com.')
    location = models.CharField(max_length=64, null=True, blank=True, help_text='Geography location for the node, appears in the account notification Email if not blank, example: Hongkong.')
    is_active = models.BooleanField(default=False, help_text='Is this node ready to be online')
    statistics = GenericRelation(Statistics, related_query_name='node')
    dt_created = models.DateTimeField('Created', auto_now_add=True)
    dt_updated = models.DateTimeField('Updated', auto_now=True)

    class Meta:
        verbose_name = 'Shadowsocks Node'

    def __init__(self, *args, **kwargs):
        super(Node, self).__init__(*args, **kwargs)
        self.ssmanager = self.get_manager()
        self.ssmanager.node = self

    def __unicode__(self):
        return '%s (%s)' % (self.public_ip, self.name)

    def get_manager(self):
        return ManagerAPI(self.manager_ip or self.public_ip, self.manager_port)

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

    @classmethod
    def get_dns_a_record(cls, domain):
        ips = []

        try:
            truename, alias, ips = socket.gethostbyname_ex(domain)
        except Exception as e:
            logger.error(e)

        return ips

    # test if Manager is up in UDP
    @property
    def is_manager_accessable(self):
        return self.ssmanager.is_accessable

    # test if dns records match the public IP
    @property
    def is_dns_record_correct(self):
        return self.public_ip in self.get_dns_a_record(self.domain)

    # test if a port is open
    def is_port_accessable(self, port, interface='public'):
        return Node.is_port_open(getattr(self, '%s_ip' % interface.lower()), port)

    def on_update(self):
        for na in self.accounts_ref.all():
            if self.is_active:
                na.on_create()
            else:
                na.on_delete()

    def toggle_active(self):
        self.is_active = not self.is_active
        self.save()

    def collect_stat(self):
        if self.is_active:
            ts = timezone.now()
            stat = self.ssmanager.ping()
            if stat:
                obj = json.loads(stat.lstrip('stat: '))

                for na in self.accounts_ref.filter(account__is_active=True):
                    na.update_stat(obj, ts)

            else:
                # do nothing if no stat data returned
                pass
        else:
            # no nothing if the node is inactive
            pass


class NodeAccount(StatisticsMethod):
    node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name='accounts_ref')
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='nodes_ref')
    statistics = GenericRelation(Statistics, related_query_name='nodeaccount')
    dt_created = models.DateTimeField('Created', auto_now_add=True)
    dt_updated = models.DateTimeField('Updated', auto_now=True)

    class Meta:
        verbose_name = 'Shadowsocks Node to Account'
        unique_together = ('node', 'account')

    def __unicode__(self):
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
    def is_accessable(self):
        return self.node.is_port_accessable(self.account.username)

    def on_create(self):
        if self.node.ssmanager.is_accessable and not self.is_created():
            retry(self.node.ssmanager.add_ex, port=self.account.username, password=self.account.password, count=5, delay=1)

    def on_delete(self, original=False):
        if original:
            port = '_original_username'
        else:
            port = 'username'

        if self.node.ssmanager.is_accessable and self.is_created(original=original):
            retry(self.node.ssmanager.remove_ex, port=getattr(self.account, port), count=5, delay=1)

    def update_stat(self, data, timestamp):
        stat, created = Statistics.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(self),
            object_id=self.pk,
            year=timestamp.year,
            month=timestamp.month)
        if stat:
            stat.update_stat(data, timestamp)
        else:
            logger.error('Failed to get or craete a %s object' % Statistics.__name__)


class ManagerAPI(object):

    def __init__(self, host, port, *args, **kwargs):
        super(ManagerAPI, self).__init__(*args, **kwargs)

        self.host = host
        self.port = port
        self.node = None # set this if belongs to a Node

    def __unicode__(self):
        return '%s:%s' % (self.host, self.port)

    def open(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
        self.socket.connect((self.host, self.port))

    def close(self):
        self.socket.close()

    def call(self, command, read=False):
        ret = None

        self.open()
        try:
            self.socket.send(bytes(command))
            if read:
                self.socket.settimeout(Config.load().timeout)
                ret = self.socket.recv(4096)
        except socket.timeout:
            logger.error('timed out on calling command: %s' % command)
        except Exception as e:
            logger.error('unexpected error: %s' % e)
            raise
        finally:
            self.close()

        return ret

    def add(self, port, password):
        command = 'add: { "server_port": %s, "password": "%s" }' % (port, password)
        self.call(command)

    def remove(self, port):
        command = 'remove: { "server_port": %s }' % port
        self.call(command)

    def ping(self):
        command = "ping"
        return self.call(command, read=True)

    def add_ex(self, port, password):
        self.add(port, password)

        return self.is_port_created(port)

    def remove_ex(self, port):
        self.remove(port)

        return not self.is_port_created(port)

    # test if a port is created with Manager API
    def is_port_created(self, port):
        stat = self.ping()
        if stat:
            obj = json.loads(stat.lstrip('stat: '))
            return obj.has_key(str(port))
        else:
            return None

    # test if the manager is in service
    @property
    def is_accessable(self):
        return self.ping() is not None


def retry(func, count=5, delay=0, *args, **kwargs):
    for i in range(count):
        ret = func(*args, **kwargs)

        if ret:
            return ret
        else:
            logger.warning('retrying %sth time in %s second(s)' % (i + 1, delay))
            time.sleep(delay)


@receiver(post_save, sender=NodeAccount)
def create_account_on_node(sender, instance, **kwargs):
    logger.info('in create_account_on_node')

    if sender == NodeAccount:
        instance.on_create()


@receiver(post_delete, sender=NodeAccount)
def delete_account_on_node(sender, instance, **kwargs):
    logger.info('in delete_account_on_node')

    if sender == NodeAccount:
        instance.on_delete()


@receiver(post_save, sender=Account)
def update_by_account(sender, instance, **kwargs):
    logger.info('in update_by_account')

    if sender == Account:
        instance.on_update()
    else:
        pass


@receiver(post_save, sender=Node)
def update_by_node(sender, instance, **kwargs):
    logger.info('in update_by_node')

    if sender == Node:
        instance.on_update()
    else:
        pass

