# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import socket
from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone


# Create your models here.

class Config(models.Model):
    port_begin = models.PositiveIntegerField('Begin port', default=8381, help_text='Port range allowed for all Shadowsocks nodes, make sure they are opened on both network firewall and host firewall.')
    port_end = models.PositiveIntegerField('End port', default=8480, help_text='Port range allowed for all Shadowsocks nodes, make sure they are opened on both network firewall and host firewall.')
    admin_name = models.CharField(max_length=32, null=True, blank=True, help_text='Appears in the account notification Email, if leave blank, the name of the logged in user will be used.')
    admin_email = models.CharField(max_length=64, null=True, blank=True, help_text='Appears in the account notification Email, if leave blank, the Email of the logged in user will be used, example: admin@shadowsocks.yourdomain.com.')
    dt_created = models.DateTimeField('Created', auto_now_add=True)
    dt_updated = models.DateTimeField('Updated', auto_now=True)

    class Meta:
        verbose_name = 'Global Configuration'

    def __unicode__(self):
        return '%s-%s' % (self.port_begin, self.port_end)

def set_year():
    return timezone.now().year

def set_month():
    return timezone.now().month


class MonthlyStatistics(models.Model):
    year = models.PositiveIntegerField(default=set_year)
    month = models.PositiveIntegerField(default=set_month)
    transferred_monthly = models.PositiveIntegerField(default=0)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    dt_calculated = models.DateTimeField('Calculated')
    dt_created = models.DateTimeField('Created', auto_now_add=True)
    dt_updated = models.DateTimeField('Updated', auto_now=True)

    class Meta:
        verbose_name_plural = 'Monthly Statistics'
        unique_together = ('year', 'month', 'content_type', 'object_id')

    def __unicode__(self):
        return '%s-%s %s %s' % (year, month, total_transferred, content_object)


class Node(models.Model):
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
    domain = models.CharField(max_length=64, null=True, blank=True, help_text='Domain name resolved to the node IP, appears in the account notification Email, if leave blank, the IP address for the node will be used, example: shadowsocks.yourdomain.com.')
    location = models.CharField(max_length=64, null=True, blank=True, help_text='Geography location for the node, appears in the account notification Email if not blank, example: Hongkong.')
    is_active = models.BooleanField(default=False, help_text='Is this node ready to be online')
    transferred_totally = models.PositiveIntegerField('Transferred', default=0, help_text='bytes transfered since the node created')
    transferred_monthly = GenericRelation(MonthlyStatistics, related_query_name='node')
    dt_created = models.DateTimeField('Created', auto_now_add=True)
    dt_updated = models.DateTimeField('Updated', auto_now=True)

    class Meta:
        verbose_name = 'Shadowsocks Node'

    def __init__(self, *args, **kwargs):
        super(Node, self).__init__(*args, **kwargs)
        if self.manager_ip and self.manager_port:
            self.ssmanager = ManagerAPI(self.manager_ip, self.manager_port)
        else:
            self.ssmanager = None

    def save(self, *args, **kwargs):
        super(Node, self).save(*args, **kwargs)
        self.ssmanager = ManagerAPI(self.manager_ip, self.manager_port)

    def __unicode__(self):
        return '%s (%s)' % (self.public_ip, self.name)

    @classmethod
    def _is_host_up(ip):
        True if os.system("ping -c 1 " + ip) is 0 else False

    @classmethod
    def _is_port_open(ip, port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((ip, int(port)))
            s.shutdown(2)
            return True
        except:
            return False

    @classmethod
    def _get_dns_a_record(domain):
        try:
            truename, alias, ips = socket.gethostbyname_ex(domain)
        except Exception as e:
            print(e)

        return ips

    def is_public_accessable(self):
        return Node._is_host_up(self.public_ip)

    def is_manager_up(self):
        return Node._is_port_open(self.manager_ip, self.manager_port)

    def is_dns_record_correct(self):
        return self.public_ip in self.get_dns_a_record(self.domain)


class Account(User):
    transferred_totally = models.PositiveIntegerField('Transferred', default=0)
    transferred_monthly = GenericRelation(MonthlyStatistics, related_query_name='account')
    date_updated = models.DateTimeField('Date Updated', auto_now=True)

    class Meta:
        verbose_name = 'Shadowsocks Account'

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
        pass # TODO


class NodeAccount(models.Model):
    node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name='accounts_ref')
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='nodes_ref')
    transferred_totally = models.PositiveIntegerField('Transferred', default=0)
    dt_created = models.DateTimeField('Created', auto_now_add=True)
    dt_updated = models.DateTimeField('Updated', auto_now=True)

    class Meta:
        verbose_name = 'Shadowsocks Node to Account'
        unique_together = ('node', 'account')

    def __unicode__(self):
        return '%s on %s' % (self.account, self.node)

    def is_alive(self):
        pass # TODO


class ManagerAPI(object):
    def __init__(self, host, port, *args, **kwargs):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
        self.socket.connect((host, port))

    def _call(self, command, read=False):
        ret = None

        try:
            self.socket.send(bytes(command))
            if read:
                ret = self.socket.recv(4096)
        except Exception as e:
            print(e)

        return ret

    def _add(self, port, password):
        command = 'add: { "server_port": %s, "password": "%s" }' % (port, password)
        return self._call(command)

    def add(self, port, password):
        # try to remove the port first, adding a port twice will remove it.
        self.remove(port)
        self._add(port, password)

    def remove(self, port):
        command = 'remove: { "server_port": %s }' % port
        return self._call(command)

    def ping(self):
        command = "ping"
        return self._call(command, read=True)

    def update(self, port, password):
        pass


@receiver(post_save, sender=NodeAccount)
def create_account_on_node(sender, instance, **kwargs):
    node = instance.node
    account = instance.account

    if account.is_active:
        node.ssmanager.add(account.username, account.password)

@receiver(post_delete, sender=NodeAccount)
def delete_account_on_node(sender, instance, **kwargs):
    node = instance.node
    account = instance.account

    node.ssmanager.remove(account.username)

@receiver(post_save, sender=Account)
def update_account_on_nodes(sender, instance, **kwargs):
    for node in instance.nodes_ref.all():
        if instance.is_active:
            create_account_on_node(None, node)
        else:
            delete_account_on_node(None, node)

@receiver(post_save, sender=Node)
def update_accounts_on_node(sender, instance, update_fields, **kwargs):
    for account in instance.accounts_ref.all():
        if instance.is_active:
            create_account_on_node(None, account)
        else:
            delete_account_on_node(None, account)

