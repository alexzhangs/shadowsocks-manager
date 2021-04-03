# -*- coding: utf-8 -*-

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals

import logging
import socket, requests, json
from collections import defaultdict
from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.sites.models import Site
from django.conf import settings


logger = logging.getLogger('django')


# Create your models here.

class Site(Site):

    class Meta:
        proxy = True

    def __str__(self):
        return self.name


class BaseNsApi(object):

    def __init__(self, user, credential, *args, **kwargs):
        super(BaseNsApi, self).__init__(*args, **kwargs)
        self.user = user
        self.credential = credential

    def call_api(self, url, method='get', data=None):
        response = getattr(requests, method)(
            url,
            auth=(self.user, self.credential),
            json=data
        )
        return response.json()

    def create_record(self, *args, **kwargs):
        pass

    def list_records(self, *args, **kwargs):
        pass

    def delete_records(self, *args, **kwargs):
        pass


class NameNsApi(BaseNsApi):

    api_base_url = 'https://api.name.com/v4'

    def create_record(self, domain, type, host, answer, ttl=300):
        url = "/".join([self.api_base_url, 'domains', domain, 'records'])
        data = {"host": host, "type": type, "answer": answer, "ttl": ttl}

        return self.call_api(url, method='post', data=data)

    def list_records(self, domain, type, host):
        url = "/".join([self.api_base_url, 'domains', domain, 'records'])

        records = self.call_api(url, method='get') or {}
        return [item for item in records.get('records', [])
                   if item.get('type') == type and item.get('host') == host]

    def delete_records(self, domain, type, host):
        records = self.list_records(domain, type, host)

        for item in records:
            url = "/".join([self.api_base_url, 'domains', domain, 'records', str(item.get('id'))])
            self.call_api(url, method='delete')

        return records

    @property
    def is_accessible(self):
        try:
            url = "/".join([self.api_base_url, 'hello'])
            return self.call_api(url, method='get').get('username') == self.user
        except:
            return False


class NameServer(models.Model):
    API_CLASS_NAME = [
        ('NameNsApi', 'NameNsApi')
    ]

    name = models.CharField(unique=True, max_length=64,
        help_text='The name for the Nameserver, name it as your wish. Example: name.com.')
    api_cls_name = models.CharField('API Class', max_length=32, choices=API_CLASS_NAME,
        help_text='Select the API class name for the Nameserver.')
    user = models.CharField(max_length=64, null=True, blank=True,
        help_text='User identity for the Nameserver API service.')
    credential = models.CharField(max_length=128, null=True, blank=True,
        help_text='User credential/token for the Nameserver API service.')
    dt_created = models.DateTimeField('Created', auto_now_add=True)
    dt_updated = models.DateTimeField('Updated', auto_now=True)

    def __str__(self):
        return self.name

    def __init__(self, *args, **kwargs):
        super(NameServer, self).__init__(*args, **kwargs)

        self.api_cls = globals().get(self.api_cls_name)

    @property
    def api(self):
        if self.api_cls and self.user and self.credential:
            return self.api_cls(self.user, self.credential)

    @property
    def is_api_accessible(self):
        return self.api.is_accessible if self.api else None


class Domain(models.Model):
    name = models.CharField(unique=True, max_length=64,
        help_text='Root domain name. Example: yourdomain.com.')
    nameserver = models.ForeignKey(NameServer, null=True, blank=True, on_delete=models.SET_NULL)
    dt_created = models.DateTimeField('Created', auto_now_add=True)
    dt_updated = models.DateTimeField('Updated', auto_now=True)

    def __str__(self):
        return self.name

    @property
    def ns_api(self):
        return self.nameserver.api if self.nameserver else None


class Record(models.Model):
    TYPE = [
        ('A', 'A'),
        ('MX', 'MX'),
        ('CNAME', 'CNAME'),
        ('TXT', 'TXT'),
        ('SRV', 'SRV'),
        ('AAAA', 'AAAA'),
        ('NS', 'NS'),
        ('ANAME', 'ANAME'),
    ]

    host = models.CharField(max_length=64,
        help_text='Host name. Example: vpn.')
    domain = models.ForeignKey(Domain, on_delete=models.PROTECT)
    type = models.CharField(max_length=8, null=True, blank=True, choices=TYPE)
    answer = models.CharField(max_length=512, null=True, blank=True,
        help_text='Answer for the host name, comma "," is the delimiter for multiple answers.')
    site = models.ForeignKey(Site, null=True, blank=True, on_delete=models.SET_NULL, related_name='records',
        help_text="The record with a site will be dynamically added to Django's ALLOWED_HOSTS.")
    dt_created = models.DateTimeField('Created', auto_now_add=True)
    dt_updated = models.DateTimeField('Updated', auto_now=True)

    class Meta:
        unique_together = ('host', 'domain')

    def __str__(self):
        return self.fqdn

    def save(self, *args, **kwargs):
        super(Record, self).save(*args, **kwargs)
        if self.site:
            self.site.domain = self.fqdn
            self.site.save()
            settings.ALLOWED_HOSTS.update_cache()

    @property
    def fqdn(self):
        return '.'.join([self.host, self.domain.name])

    @property
    def answers(self):
        """
        Return the record.answer in lowercase and split as Set.
        """
        return {
            item.lower()
            for item in (self.answer.split(',') if self.answer else [])
        }

    @property
    def answer_from_dns_api(self):
        """
        Return the answers from DNS API, in lowercase and as Set.
        """
        if self.domain.ns_api:
            return {
                record.get('answer').lower()
                for record in self.domain.ns_api.list_records(
                    self.domain.name, self.type, self.host
                )
            }

    @property
    def answer_from_dns_query(self):
        """
        Return the answers from DNS query, in lowercase and as Set.
        """
        ips = []
        try:
            truename, alias, ips = socket.gethostbyname_ex(self.fqdn)
        except socket.gaierror:
            # not found the host
            pass
        except Exception as e:
            logger.error(e)
        return {item.lower() for item in ips}

    @property
    def is_matching_dns_api(self):
        """
        Test if the record.answer matches the DNS API query.
        """
        return self.answers == self.answer_from_dns_api

    @property
    def is_matching_dns_query(self):
        """
        Test if the record.answer matches the DNS query.
        """
        return self.answers == self.answer_from_dns_query

    def sync_to_dns(self):
        """
        Sync the record to DNS server through DNS API.
        """
        ret = defaultdict(list)
        if self.domain.ns_api:
            if self.is_matching_dns_api:
                ret['message'] = 'No need to synchronize.'
                return ret

            ret['deleted'] = self.delete_from_dns()
            for answer in (self.answer or '').split(','):
                ret['created'].append(
                    self.domain.ns_api.create_record(self.domain.name, self.type, self.host, answer))
        else:
            ret['message'] = 'Please configure Nameserver and its User and Credential for the domain first.'

        return ret

    def delete_from_dns(self):
        """
        Delete the record from DNS server through DNS API.
        """
        if self.domain.ns_api:
            return self.domain.ns_api.delete_records(self.domain.name, self.type, self.host)


@receiver(post_save, sender=Record)
def record_sync_to_dns(sender, instance, **kwargs):
    instance.sync_to_dns()


@receiver(post_delete, sender=Record)
def record_delete_from_dns(sender, instance, **kwargs):
    instance.delete_from_dns()
