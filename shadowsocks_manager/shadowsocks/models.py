# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone


# Create your models here.

class BaseModel(models.Model):
    dt_created = models.DateTimeField('Created', auto_now_add=True)
    dt_updated = models.DateTimeField('Updated', auto_now=True)


class Config(BaseModel):
    port_begin = models.PositiveIntegerField('Begin port', default=8381, help_text='Port range allowed for all Shadowsocks nodes, make sure they are opened on both network firewall and host firewall.')
    port_end = models.PositiveIntegerField('End port', default=8480, help_text='Port range allowed for all Shadowsocks nodes, make sure they are opened on both network firewall and host firewall.')
    admin_name = models.CharField(max_length=32, null=True, blank=True, help_text='Appears in the account notification Email, if leave blank, the name of the logged in user will be used.')
    admin_email = models.CharField(max_length=64, null=True, blank=True, help_text='Appears in the account notification Email, if leave blank, the Email of the logged in user will be used, example: admin@shadowsocks.yourdomain.com.')

    class Meta:
        verbose_name = 'Global Configuration'

    def __unicode__(self):
        return '%s-%s' % (self.port_begin, self.port_end)

def set_year():
    return timezone.now().year

def set_month():
    return timezone.now().month


class MonthlyStatistics(BaseModel):
    year = models.PositiveIntegerField(default=set_year)
    month = models.PositiveIntegerField(default=set_month)
    transferred_monthly = models.PositiveIntegerField(default=0)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    dt_calculated = models.DateTimeField('Calculated')

    class Meta:
        verbose_name_plural = 'Monthly Statistics'
        unique_together = ('year', 'month', 'content_type', 'object_id')

    def __unicode__(self):
        return '%s-%s %s %s' % (year, month, total_transferred, content_object)


class Node(BaseModel):
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
    domain_name = models.CharField('Domain', max_length=64, null=True, blank=True, help_text='Domain name resolved to the node IP, appears in the account notification Email, if leave blank, the IP address for the node will be used, example: shadowsocks.yourdomain.com.')
    location = models.CharField(max_length=64, null=True, blank=True, help_text='Geography location for the node, appears in the account notification Email if not blank, example: Hongkong.')
    is_active = models.BooleanField(default=False, help_text='Is this node ready to be online')
    transferred_totally = models.PositiveIntegerField('Transferred', default=0, help_text='bytes transfered since the node created')
    transferred_monthly = GenericRelation(MonthlyStatistics, related_query_name='ssnode')

    class Meta:
        verbose_name = 'Shadowsocks Node'

    def __unicode__(self):
        return '%s (%s)' %(self.name, self.public_ip)




class Account(User):
    transferred_totally = models.PositiveIntegerField('Transferred', default=0)
    transferred_monthly = GenericRelation(MonthlyStatistics, related_query_name='account')
    date_updated = models.DateTimeField('Date Updated', auto_now=True)

    class Meta:
        verbose_name = 'Shadowsocks Account'

    def __unicode__(self):
        return '%s(%s)' % (self.get_username(), self.get_full_name())

    def save(self, *args, **kwargs):
        obj = Group.objects.get(name='shadowsocks-clients')
        if obj not in self.groups.all():
            self.groups.add(obj)
        return super(Account, self).save(*args, **kwargs)


class NodeAccount(BaseModel):
    ssnode = models.ForeignKey('Node', Node, related_name='ssnodes')
    account = models.ForeignKey(Account, related_name='accounts')
    transferred_totally = models.PositiveIntegerField('Transferred', default=0)

    class Meta:
        verbose_name = 'Shadowsocks Node to Account'
        unique_together = ('ssnode', 'account')

    def __unicode__(self):
        return '%s on %s' % (account, ssnode)
