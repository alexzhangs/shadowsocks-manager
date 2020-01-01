# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import requests, json
from django.db import models


# Create your models here.

class DomainManager(object):

    class Meta:
        abstract = True

    def __init__(self, user, credential, *args, **kwargs):
        super(DomainManager, self).__init__(*args, **kwargs)
        self.user = user
        self.credential = credential

    def call_api(self, url, method='get', data=None):
        response = getattr(requests, method)(
            url,
            auth=(self.user, self.credential),
            json=data
        )
        return json.loads(response.text) or response

    def create_record(self, *args, **kwargs):
        pass

    def list_records(self, *args, **kwargs):
        pass

    def delete_records(self, *args, **kwargs):
        pass


class NameDomainManager(DomainManager):

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
    def is_accessable(self):
        try:
            url = "/".join([self.api_base_url, 'hello'])
            return self.call_api(url, method='get').get('username') == self.user
        except:
            return False


class Domain(models.Model):

    NAMESERVER = [
        ('name.com', 'Name.com')
    ]

    name = models.CharField(unique=True, max_length=64,
        help_text='Domain name. Example: vpn.yourdomain.com.')
    nameserver = models.CharField(max_length=32, choices=NAMESERVER, null=True, blank=True,
        help_text='Select the Nameserver for the domain.')
    user = models.CharField(max_length=64, null=True, blank=True,
        help_text='User identity for the Nameserver API service.')
    credential = models.CharField(max_length=128, null=True, blank=True,
        help_text='User credential/token for the Nameserver API service.')
    dt_created = models.DateTimeField('Created', auto_now_add=True)
    dt_updated = models.DateTimeField('Updated', auto_now=True)

    class Meta:
        verbose_name = 'Domain Name'

    def __unicode__(self):
        return self.name

    def __init__(self, *args, **kwargs):
        super(Domain, self).__init__(*args, **kwargs)

        items = self.name.split(".")
        bound = len(items) - 2
        self.host = ".".join(items[0:bound])
        self.second_level_domain = ".".join(items[bound:])

        if self.nameserver:
            cls = globals().get(
                '{prefix}DomainManager'.format(prefix=self.nameserver.split(".")[0].title())
            )
        else:
            cls = None

        if cls and self.user and self.credential:
            self.manager = cls(self.user, self.credential)
        else:
            self.manager = None

    @property
    def is_manager_accessable(self):
        if self.manager:
            return self.manager.is_accessable

    @property
    def active_dns_records(self):
        if self.manager:
            return ",".join([record.get('answer') for record in self.manager.list_records(self.second_level_domain, 'A', self.host)])

    @property
    def active_nodes(self):
        return ",".join([node.public_ip for node in self.nodes.all() if node.is_active and node.public_ip])

    def sync(self):
        ret = {
            'deleted': [],
            'created': []
        }
        if self.manager:
            if self.active_dns_records == self.active_nodes:
                ret['message'] = 'No need to synchronize.'
                return ret

            ret['deleted'].extend(self.manager.delete_records(self.second_level_domain, 'A', self.host))
            for node in self.nodes.all():
                if node.is_active and node.public_ip:
                    ret['created'].append(self.manager.create_record(self.second_level_domain, 'A', self.host, node.public_ip))
        else:
            ret['message'] = 'Please configure Nameserver and its User and Credential for the domain first.'

        return ret
