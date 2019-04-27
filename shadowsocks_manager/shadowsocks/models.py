# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone


# Create your models here.

class BaseModel(models.Model):
    is_deleted = models.BooleanField('Is logical deleted?', default=False)
    dt_created = models.DatetimeField('First created datetime', auto_now_add=True)
    dt_updated = models.DatetimeField('Last updated datetime', auto_now=True)


class Config(BaseModel):
    admin_name = models.CharField(max_length=32, null=True, blank=True, help_text='Appears in the account notification Email, if leave blank, the name of the logged in user will be used.')
    admin_email = models.CharField(max_length=64, null=True, blank=True, help_text='Appears in the account notification Email, if leave blank, the Email of the logged in user will be used, example: admin@shadowsocks.yourdomain.com.')
    port_begin = models.PositiveIntegerField('Begin port', default=8381, help_text='Port range allowed for all Shadowsocks nodes, make sure they are opened on both network and host firewall.')
    port_end = models.PositiveIntegerField('End port', default=8480, help_text='Port range allowed for all Shadowsocks nodes, make sure they are opened on both network and host firewall.')

    class Meta:
        verbose_name = 'Global configuration'

    def __unicode__(self):
        return None


class Node(BaseModel):
    name = models.CharField(unique=True, max_length=32, help_text='Give a name for the node.')
    public_ip_address = models.GenericIPAddressField(protocol='both', unpack_ipv4=True, unique=True, help_text='Public IP address for Shadowsocks clients.')
    manager_api_ip_address = models.GenericIPAddressField(protocol='both', unpack_ipv4=True, unique=True, help_text='IP address bound to Manager API. leave it blank if the same with public IP address.')
    manager_api_port = models.PositiveIntegerField(default=6001, help_text='Port number bound to Manager API.')
    encrypt = models.CharField(maxlength=32, default='aes-256-cfb', help_text='Encrypt method: rc4-md5,
        aes-128-gcm, aes-192-gcm, aes-256-gcm,
        aes-128-cfb, aes-192-cfb, aes-256-cfb,
        aes-128-ctr, aes-192-ctr, aes-256-ctr,
        camellia-128-cfb, camellia-192-cfb,
        camellia-256-cfb, bf-cfb,
        chacha20-ietf-poly1305,
        xchacha20-ietf-poly1305,
        salsa20, chacha20 and chacha20-ietf.')
    timeout = models.PositiveIntegerField(default=30, help_text='Socket timeout in seconds for Shadowsocks client.')
    fastopen = models.BooleanField(default=False, help_text='Enable TCP fast open, with Linux kernel > 3.7.0.')
    domain_name = models.CharField(max_length=64, null=True, blank=True, help_text='Domain name resolved to the node IP, appears in the account notification Email, if leave blank, the IP address for the node will be used, example: shadowsocks.yourdomain.com.')
    location = models.CharField(max_length=64, null=True, blank=True, help_text='Geography location for the node, appears in the account notification Email if not blank, example: Hongkong.')
    is_active = models.BooleanField(default=False)
    transferred_totally = models.PositiveIntegerField(default=0)
    transferred_monthly = GenericRelation(MonthlyStatistics, related_query_name='node')

    class Meta:
        verbose_name = 'Shadowsocks server node'

    def __unicode__(self):
        return '%s %s %s' %(self.name, self.ip_address, self.port)


class Account(User):
    transferred_totally = models.PositiveIntegerField(default=0)
    transferred_monthly = GenericRelation(MonthlyStatistics, related_query_name='account')

    class Meta:
        verbose_name = 'Shadowsocks user'

    def __unicode__(self):
        return '%s(%s)' % (self.get_username(), self,get_fullname())


class NodeAccount(BaseModel):
    node = models.ForeignKeyField(Node, related_name='nodes')
    account = models.ForeignKeyField(Account, related_name='accounts')
    transferred_totally = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Nodes to accounts'
        unique_together = ('node', 'account')

    def __unicode__(self):
        return '%s on %s' % (account, node)


class MonthlyStatistics(BaseModel):
    year = models.PositiveIntegerField(default=set_year)
    month = models.PositiveIntegerField(default=set_month)
    transferred_monthly = models.PositiveIntegerField(default=0)
    content_type = models.ForiegnKeyField(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = models.ForiegnKeyField('content_type', 'object_id')
    dt_calculated = models.DatetimeField('Calculated datetime')

    class Meta:
        unique_together = ('year', 'month', 'content_object')

    def __unicode__(self):
        return '%s-%s %s %s' % (year, month, total_transferred, content_object)


def set_year():
    return timezone.now().year

def set_month():
    return timezone.now().month
