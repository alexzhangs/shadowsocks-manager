# -*- coding: utf-8 -*-

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals
from __future__ import absolute_import

import os
import re
import copy
import logging
from contextlib import contextmanager
import dns.resolver, tldextract
from lexicon import config, client
from collections import defaultdict
from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.sites.models import Site
from django.conf import settings
from allowedsites import CachedAllowedSites


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


@contextmanager
def temporary_environment(variables):

    def clear_env():
        try:
            os.environ.clear()
        except OSError:
            # python 3.7, 3.8 allow empty key but fail to clear the environment
            os.environ = {}

    original = os.environ.copy()
    try:
        clear_env()
        os.environ.update(variables)
        yield
    finally:
        clear_env()
        os.environ.update(original)
        
        
class DnsApi(object):
    """
    https://dns-lexicon.readthedocs.io/en/latest/provider_conventions.html
    """
    def __init__(self, env, domain):
        self.env = env
        self.domain = domain
        self.envs = {}
        self.config = config.ConfigResolver()

        for item in env.split(','):
            # split with only the first '=', ignore the rest
            key, value = item.split('=', 1)
            self.envs[key] = value

        with temporary_environment(self.envs):
            self.config.with_env().with_dict({
                'domain': domain,
            })

    def call(self, method, *args):
        logger.info('{domain}: {method}({args})'.format(domain=self.domain, method=method, args=args))
        try:
            with client.Client(self.config) as operations:
                return getattr(operations, method)(*args)
        except Exception as e:
            logger.error('{}: {}: {}: {}'.format(self.domain, getattr(e, '__module__', 'call'), type(e).__name__, e))
            return None
    
    def list_records(self, type, name=None, content=None):
        """
        Normal Behaviour: List all records. If filters are provided, send to the API if possible, else apply filter locally. Return value should be a list of records.
        Record Sets: Ungroup record sets into individual records. Eg: If a record set contains 3 values, provider ungroup them into 3 different records.
        Linked Records: For services that support some form of linked record, do not resolve, treat as CNAME.
        """
        return self.call('list_records', type, name, content)

    def create_record(self, type, name, content):
        """
        Normal Behavior: Create a new DNS record. Return a boolean True if successful.
        If Record Already Exists: Do nothing. DO NOT throw exception.
        TTL: If not specified or set to 0, use reasonable default.
        Record Sets: If service supports record sets, create new record set or append value to existing record set as required.
        """
        return self.call('create_record', type, name, content)

    def update_record(self, type, name, content):
        """
        Normal Behaviour: Update a record. Record to be updated can be specified by providing id OR name, type and content. Return a boolean True if successful.
        Record Sets: If matched record is part of a record set, only update the record that matches. Update the record set so that records other than the matched one are unmodified.
        TTL:
            If not specified, do not modify ttl.
            If set to 0, reset to reasonable default.
        No Match: Throw exception?
        """
        return self.call('update_record', None, type, name, content)

    def delete_record(self, type, name, content=None):
        """
        Normal Behaviour: Remove a record. Record to be deleted can be specified by providing id OR name, type and content. Return a boolean True if successful.
        Record sets: Remove only the record that matches all the filters.
            If content is not specified, remove the record set.
            If length of record set becomes 0 after removing record, remove the record set.
            Otherwise, remove only the value that matches and leave other records as-is.
        No Match: Do nothing. DO NOT throw exception
        """
        return self.call('delete_record', None, type, name, content)

    @property
    def is_accessible(self):
        return self.list_records('A', 'whatever') is not None


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


class CustomDomainManager(models.Manager):
    def resolve_name(self, kwargs):
        if 'name' in kwargs:
            kwargs['name'] = get_zone_name(kwargs['name'])
        return kwargs

    def get(self, *args, **kwargs):
        kwargs = self.resolve_name(kwargs)
        return super(CustomDomainManager, self).get(*args, **kwargs)

    def filter(self, *args, **kwargs):
        kwargs = self.resolve_name(kwargs)
        return super(CustomDomainManager, self).filter(*args, **kwargs)

    def get_or_create(self, *args, **kwargs):
        kwargs = self.resolve_name(kwargs)
        return super(CustomDomainManager, self).get_or_create(*args, **kwargs)

    def update_or_create(self, *args, **kwargs):
        kwargs = self.resolve_name(kwargs)
        return super(CustomDomainManager, self).update_or_create(*args, **kwargs)
    

class Domain(models.Model):
    name = models.CharField(unique=True, max_length=64,
        help_text='Domain name. Example: `example.com`. '
        'If the domain name is not root domain name, the zone name will be resolved automatically. ')
    nameserver = models.ForeignKey(NameServer, null=True, blank=True, on_delete=models.SET_NULL)
    dt_created = models.DateTimeField('Created', auto_now_add=True)
    dt_updated = models.DateTimeField('Updated', auto_now=True)

    objects = CustomDomainManager()

    def __str__(self):
        return self.name

    @property
    def api(self):
        if self.nameserver and self.nameserver.env:
            try:
                return DnsApi(self.nameserver.env, self.name)
            except Exception as e:
                logger.error('DnsApi: domain ({0}), env ({1}): {2}: {3}'.format(self.name, self.nameserver.env, type(e).__name__, e))
        else:
            logger.warning('{0}: please configure nameserver properly for the domain to enable DnsApi.'.format(self.name))

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
        help_text='Fully Qualified Domain Name. Example: `vpn.example.com`. '
        'The `host` and `domain` (zone name) will be automatically resolved. '
        'if both `host` and `domain` are set, this field will be ignored.')
    host = models.CharField(max_length=64,
        help_text='Host name without domain name. Example: `vpn`.')
    domain = models.ForeignKey(Domain, on_delete=models.PROTECT)
    type = models.CharField(max_length=8, choices=TYPE)
    answer = models.CharField(max_length=512,
        help_text='Answer for the host name, comma "," is the delimiter for multiple answers.')
    site = models.ForeignKey(Site, null=True, blank=True, on_delete=models.SET_NULL, related_name='records',
        help_text="The record with a site will be dynamically added to Django's ALLOWED_HOSTS.")
    dt_created = models.DateTimeField('Created', auto_now_add=True)
    dt_updated = models.DateTimeField('Updated', auto_now=True)

    class Meta:
        unique_together = ('host', 'domain')

    def __init__(self, *args, **kwargs):
        super(Record, self).__init__(*args, **kwargs)
        self.auto_resolve()
        # take a snapshot of the original record
        self.origin = copy.deepcopy(self)

    def __str__(self):
        return self.fqdn
    
    def save(self, *args, **kwargs):
        self.auto_resolve()
        super(Record, self).save(*args, **kwargs)

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

    def update_site_domain(self):
        """
        Update the associated site domain with the record fqdn.
        """
        if self.site:
            self.site.domain = self.fqdn
            self.site.save()

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
    def dnsapi(self):
        return self.domain.api if self.domain else None

    @property
    def answer_from_dns_api(self):
        """
        Return the answers from DNS API, in lowercase and as Set.
        """
        if self.dnsapi:
            return {
                record.get('content').lower()
                for record in self.dnsapi.list_records(self.type, self.host) or []
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
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
            # no answer for the host
            return {}
        except Exception as e:
            logger.error('{} {}: {}: {}: {}'.format(self.fqdn, self.type, getattr(e, '__module__', 'answer_from_dns_query'), type(e).__name__, e))

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

    def on_update(self):
        """
        The matrix of rules for the update event:
        +--------+--------------+-------------------------------------------------+
        |  field |       /      |                   TYPE or HOST                  |
        +========+==============+========================+========================+
        |    /   | change state |            X           |            √           |
        +--------+--------------+------------------------+------------------------+
        |        |              | rs.dns_delete()        | rs.origin.dns_delete() |
        |        |       X      | rs.dns_create()        | rs.dns_delete()        |
        |        |              |                        | rs.dns_create()        |
        | DOMAIN +--------------+------------------------+------------------------+
        |        |              | rs.origin.dns_delete() | rs.origin.dns_delete() |
        |        |       √      | rs.dns_delete()        | rs.dns_delete()        |
        |        |              | rs.dns_create()        | rs.dns_create()        |
        +--------+--------------+------------------------+------------------------+
        """
        self.update_site_domain()

        deleted_origin = None
        try:
            if self.domain != self.origin.domain or self.host != self.origin.host or self.type != self.origin.type:
                # clean up the old record
                deleted_origin = self.origin.dns_delete()
        except models.ObjectDoesNotExist:
            # ignore an empty record without domain
            pass

        ret = self.dns_sync()
        ret['deleted']['origin'] = deleted_origin
        return ret

    def on_delete(self):
        return self.dns_delete()

    def dns_sync(self):
        """
        Sync the record to DNS server through DNS API.
        """
        ret = defaultdict(dict)
        
        if self.dnsapi:
            if self.is_matching_dns_api:
                ret['message'] = 'No need to synchronize.'
                return ret

            ret['deleted'] = self.dns_delete()
            ret['created'] = self.dns_create()
        else:
            ret['message'] = 'Please configure Nameserver properly for the domain first.'

        return ret

    def dns_create(self):
        """
        Create the recordset to DNS server through DNS API.
        Return:
            {}
            {'true': [<answer>, ...]}
            {'null': [<answer>, ...]}
            {'true': [<answer>, ...], 'null': [<answer>, ...]}
        """
        ret = defaultdict(list)
        if self.dnsapi and not self.is_matching_dns_api:
            for answer in self.answers:
                created = self.dnsapi.create_record(self.type, self.host, answer)
                ret[created].append(answer)
        return ret

    def dns_delete(self):
        """
        Delete the recordset from DNS server through DNS API.
        Return:
            {}
            {'true': <type>}
            {'null': <type>}
        """
        ret = defaultdict(str)
        if self.dnsapi and self.dnsapi.list_records(self.type, self.host):
            deleted = self.dnsapi.delete_record(self.type, self.host)
            ret[deleted] = self.type
        return ret


@receiver(post_save, sender=Site)
def allowedsites_update_cache(sender, instance, **kwargs):
    # Django test framework overrides the settings.ALLOWED_HOSTS to an list
    if isinstance(settings.ALLOWED_HOSTS, CachedAllowedSites):
        settings.ALLOWED_HOSTS.update_cache()

@receiver(post_save, sender=Record)
def record_on_update(sender, instance, **kwargs):
    instance.on_update()

@receiver(post_delete, sender=Record)
def record_on_delete(sender, instance, **kwargs):
    instance.on_delete()
