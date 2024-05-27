# -*- coding: utf-8 -*-

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals

import os
import re
import logging
import dns.resolver, tldextract
import lexicon
from collections import defaultdict
from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.sites.models import Site
from django.conf import settings


logger = logging.getLogger(__name__)


# Create your models here.

def get_host_name(domain):
    """
    Return the part before the root domain name or the delegated subdomain name.
    e.g.:
        foo.bar.example.co.uk           -> foo.bar
        foo.zone2.zone1.example.co.uk   -> foo
        example.co.uk                   -> ''
        zone2.zone1.example.co.uk       -> ''
    """
    if domain:
        zone = get_zone_name(domain)
        return re.sub('([.]|^)' + zone + '$', '', domain) if zone else None

def get_zone_name(domain):
    """
    Return the root domain name or the delegated subdomain name.
    If the domain is not resolvable, fallback to use the root domain name.
    e.g.:
        foo.bar.example.co.uk           -> example.co.uk
        foo.zone2.zone1.example.co.uk   -> zone2.zone1.example.co.uk
        example.co.uk                   -> example.co.uk
        zone2.zone1.example.co.uk       -> zone2.zone1.example.co.uk
    """
    if domain:
        extract = tldextract.TLDExtract()
        # deal with py2 and py3 compatibility
        compat_method = extract.extract if hasattr(extract, 'extract') else extract
        result = compat_method(domain)

        # get the root domain name
        root = result.registered_domain
        if domain == root:
            # no need to resolve the domain
            return domain

        zone = dns.resolver.zone_for_name(domain).to_text(omit_final_dot=True)
        # get the tld from the domain
        tld = result.suffix
        if zone == tld:
            # the domain is not resolvable, fallback to use the root domain
            zone = root
        return zone


class Site(Site):

    class Meta:
        proxy = True

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super(Site, self).save(*args, **kwargs)
        settings.ALLOWED_HOSTS.update_cache()

class DnsApi:
    """
    https://dns-lexicon.readthedocs.io/en/latest/provider_conventions.html
    """
    def __init__(self, env, domain):
        self.config = lexicon.config.ConfigResolver()

        # export the environment variables
        for item in env.split(','):
            # split with only the first '=', ignore the rest
            key, value = item.split('=', 1)
            os.environ[key] = value

        self.config.with_env().with_dict({
            'domain': domain,
        })

    def call(self, method, *args):
        try:
            with lexicon.client.Client(self.config) as operations:
                return getattr(operations, method)(*args)
        except Exception as e:
            logger.error(e)
            return None
    
    def list_records(self, type, name=None, content=None):
        return self.call('list_records', type, name, content)

    def create_record(self, type, name, content):
        return self.call('create_record', type, name, content)

    def update_record(self, type, name, content):
        return self.call('update_record', None, type, name, content)

    def delete_record(self, type, name, content=None):
        return self.call('delete_record', None, type, name, content)

    @property
    def is_accessible(self):
        try:
            return self.list_records('A', 'whatever') is not None
        except Exception as e:
            logger.error(e)
            return False


class NameServer(models.Model):
    name = models.CharField(unique=True, max_length=64,
        help_text='The name for the Nameserver, name it as your wish. Example: `name.com`.')
    env = models.CharField(max_length=512, null=True, blank=True,
        help_text='Environment variables required to use the DNS API service.<br>'
            'Syntax: `LEXICON_PROVIDER_NAME={dns_provider},LEXICON_{DNS_PROVIDER}_{OPTION}={value}[,...]`<br>'
            'The Python library `dns-lexicon` is leveraged to parse the DNS_ENV and access the DNS API.<br>'
            'The required {OPTION} depends on the {dns_provider} that you use.<br>'
            'Sample: `LEXICON_PROVIDER_NAME=namecom,LEXICON_NAMECOM_AUTH_USERNAME=your_username,LEXICON_NAMECOM_AUTH_TOKEN=your_token`<br>'
            'Link: https://dns-lexicon.readthedocs.io/en/latest/configuration_reference.html')
    dt_created = models.DateTimeField('Created', auto_now_add=True)
    dt_updated = models.DateTimeField('Updated', auto_now=True)

    def __str__(self):
        return self.name


class DomainManager(models.Manager):
    def resolve_name(self, kwargs):
        if 'name' in kwargs:
            kwargs['name'] = get_zone_name(kwargs['name'])
        return kwargs

    def get(self, *args, **kwargs):
        kwargs = self.resolve_name(kwargs)
        return super(DomainManager, self).get(*args, **kwargs)

    def filter(self, *args, **kwargs):
        kwargs = self.resolve_name(kwargs)
        return super(DomainManager, self).filter(*args, **kwargs)

    def get_or_create(self, *args, **kwargs):
        kwargs = self.resolve_name(kwargs)
        return super(DomainManager, self).get_or_create(*args, **kwargs)

    def update_or_create(self, *args, **kwargs):
        kwargs = self.resolve_name(kwargs)
        return super(DomainManager, self).update_or_create(*args, **kwargs)
    

class Domain(models.Model):
    name = models.CharField(unique=True, max_length=64,
        help_text='Domain name. Example: `example.com`. '
        'If the domain name is not root domain name, the zone name will be resolved automatically. ')
    nameserver = models.ForeignKey(NameServer, null=True, blank=True, on_delete=models.SET_NULL)
    dt_created = models.DateTimeField('Created', auto_now_add=True)
    dt_updated = models.DateTimeField('Updated', auto_now=True)

    objects = DomainManager()

    def __str__(self):
        return self.name

    def __init__(self, *args, **kwargs):
        super(Domain, self).__init__(*args, **kwargs)

        self.api = None
        if self.nameserver and self.nameserver.env:
            try:
                self.api = DnsApi(self.nameserver.env, self.name)
            except Exception as e:
                logger.error('DnsApi: domain ({0}), env ({1}): {2}'.format(self.name, self.nameserver.env, e))

    def save(self, *args, **kwargs):
        self.auto_resolve()

        super(Domain, self).save(*args, **kwargs)

    def auto_resolve(self):
        """
        Resolve the root domain name or the delegated subdomain name from the domain name.
        """
        if self.name:
            self.name = get_zone_name(self.name)

    @property
    def is_api_accessible(self):
        return self.api.is_accessible if self.api else None


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

    fqdn = models.CharField(unique=True, max_length=128,
        help_text='Fully Qualified Domain Name. Example: `vpn.yourdomain.com`. '
        'The `host` and `domain` (zone name) will be automatically resolved. '
        'if both `host` and `domain` are set, this field will be ignored.')
    host = models.CharField(max_length=64,
        help_text='Host name without domain name. Example: `vpn`.')
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
        self.auto_resolve()

        super(Record, self).save(*args, **kwargs)

        # update the site domain
        if self.site:
            self.site.domain = self.fqdn
            self.site.save()

    def auto_resolve(self):
        """
        Resolve the host and domain from the fqdn if they are not set.
        Resolve the fqdn from the host and domain if it is not set.
        """
        if self.host and self.domain:
            self.fqdn = '.'.join([self.host, self.domain.name])
        elif self.fqdn:
            self.host = get_host_name(self.fqdn)
            self.domain = Domain.objects.get(name=get_zone_name(self.fqdn))

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
        if self.domain.api:
            return {
                record.get('content').lower()
                for record in self.domain.api.list_records(self.type, self.host) or []
            }

    @property
    def answer_from_dns_query(self):
        """
        Return the answers from DNS query, in lowercase and as Set.
        """
        try:
            # deal with py2 and py3 compatibility
            compat_method = dns.resolver.query if hasattr(dns.resolver, 'query') else dns.resolver.resolve
            answers = compat_method(self.fqdn, self.type)

            return {item.to_text().lower() for item in answers}
        except dns.resolver.NXDOMAIN:
            # not found the host
            return {}
        except Exception as e:
            logger.error(e)

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
        if self.domain.api:
            if self.is_matching_dns_api:
                ret['message'] = 'No need to synchronize.'
                return ret

            ret['deleted'] = self.delete_from_dns()
            for answer in (self.answer or '').split(','):
                ret['created'].append(self.domain.api.create_record(self.type, self.host, answer))
        else:
            ret['message'] = 'Please configure Nameserver properly for the domain first.'

        return ret

    def delete_from_dns(self):
        """
        Delete the record from DNS server through DNS API.
        """
        if self.domain.api:
            return self.domain.api.delete_record(self.type, self.host)


@receiver(post_save, sender=Record)
def record_sync_to_dns(sender, instance, **kwargs):
    instance.sync_to_dns()


@receiver(post_delete, sender=Record)
def record_delete_from_dns(sender, instance, **kwargs):
    instance.delete_from_dns()
