# -*- coding: utf-8 -*-

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals
from __future__ import absolute_import

import json
import os
from abc import abstractmethod
from django.test import TestCase
from django.core.management import call_command

from domain import models, serializers


import logging
# Get a logger for this django app
logger = logging.getLogger(__name__.split('.')[-2])
# Set the logging level to make the output clean
logger.setLevel(logging.CRITICAL)


class BaseTestCase(TestCase):
    """
    A base test case for current app.
    This class is inherited from Django TestCase class, and provides the following features:

    Set a list of default fixtures for all test cases in this app.
    * fixtures = []

    Set a list of test case class names, if the up() and down() class methods are defined in
    the sub-class, all of them can be called at once by calling the allup() and alldown() class 
    methods in this class.
    * testcases = []
    """

    fixtures = []
    testcases = []

    class meta:
        abstract = True

    @classmethod
    @abstractmethod
    def up(cls):
        """
        Set up the test environment.
        """
        pass

    @classmethod
    @abstractmethod
    def down(cls):
        """
        Tear down the test environment.
        """
        pass

    @classmethod
    def allup(cls):
        """
        Call the up() class method (if exists) in each class defined in the testcases list.
        """
        for testcase in [globals().get(name) for name in cls.testcases]:
            method = getattr(testcase or {}, 'up', None)
            if method: method()

    @classmethod
    def alldown(cls):
        """
        Call the down() class method (if exists) in each class defined in the testcases list.
        """
        for testcase in [globals().get(name) for name in cls.testcases]:
            method = getattr(testcase or {}, 'down', None)
            if method: method()


class AppTestCase(BaseTestCase):
    fixtures = []
    testcases = ['DnsApiTestCase', 'NameServerTestCase', 'DomainTestCase', 'RecordTestCase', 'ManagementCommandTestCase']


class DnsApiTestCase(AppTestCase):
    def test_dnsapi_init_positive(self):
        env = 'KEY1=VALUE=1,KEY2=VALUE2=2'
        domain = 'example.com'
        obj = models.DnsApi(env=env, domain=domain)
        self.assertEqual(obj.envs['KEY1'], 'VALUE=1')
        self.assertEqual(obj.envs['KEY2'], 'VALUE2=2')
        self.assertEqual(obj.config.resolve('domain'), domain)

    def test_dnsapi_init_env_isolation(self):
        envs = ['LEXICON_PROVIDER_NAME=mockprovider-1', 'LEXICON_PROVIDER_NAME=mockprovider-2']
        domains = ['example.com', 'example.org']
        for i in range(2):
            obj = models.DnsApi(env=envs[i], domain=domains[i])
            self.assertEqual(obj.config.resolve('lexicon:provider_name'), 'mockprovider-%d' % (i + 1))
            self.assertEqual(obj.config.resolve('domain'), domains[i])

    def test_dns_api_init_env_clear(self):
        env = 'KEY1=VALUE1,KEY2=VALUE2'
        domain = 'example.com'
        obj = models.DnsApi(env=env, domain=domain)
        self.assertFalse(os.environ.get('KEY1'))
        self.assertFalse(os.environ.get('KEY2'))

    def test_dnsapi_init_positive_mockprovider(self):
        env = 'PROVIDER=mockprovider,LEXICON_PROVIDER_NAME=mockprovider,LEXICON_MOCKPROVIDER_MOCKUSER=mockuser,LEXICON_MOCKPROVIDER_MOCKTOKEN=mocktoken'
        domain = 'example.com'
        obj = models.DnsApi(env=env, domain=domain)
        self.assertEqual(obj.config.resolve('lexicon:provider_name'), 'mockprovider')
        self.assertEqual(obj.config.resolve('lexicon:mockprovider:mockuser'), 'mockuser')
        self.assertEqual(obj.config.resolve('lexicon:mockprovider:mocktoken'), 'mocktoken')
        self.assertEqual(obj.config.resolve('domain'), domain)

    def test_dnsapi_init_negative(self):
        domain = 'example.com'
        self.assertRaises(AttributeError, models.DnsApi, None, domain)
        self.assertRaises(ValueError, models.DnsApi, '', domain)

    def test_dnsapi_call_negative(self):
        obj = models.DnsApi('KEY=VALUE', 'example.com')
        self.assertFalse(obj.call('list_records', 'A'))

    def test_dnsapi_is_accessible_negative_mockprovider(self):
        env = 'PROVIDER=mockprovider,LEXICON_PROVIDER_NAME=mockprovider,LEXICON_MOCKPROVIDER_MOCKUSER=mockuser,LEXICON_MOCKPROVIDER_MOCKTOKEN=mocktoken'
        obj = models.DnsApi(env, 'example.com')
        self.assertFalse(obj.is_accessible)

    def test_dnsapi_is_accessible_negative_namecom(self):
        env = 'PROVIDER=namecom,LEXICON_PROVIDER_NAME=namecom,LEXICON_NAMECOM_AUTH_USERNAME=mockuser,LEXICON_NAMECOM_AUTH_TOKEN=mocktoken'
        obj = models.DnsApi(env, 'example.com')
        self.assertFalse(obj.is_accessible)


class NameServerTestCase(AppTestCase):
    @classmethod
    def up(cls):
        # add nameserver
        obj = models.NameServer(name='mocknameserver', env='PROVIDER=mockprovider,LEXICON_PROVIDER_NAME=mockprovider,LEXICON_MOCKPROVIDER_MOCKUSER=mockuser,LEXICON_MOCKPROVIDER_MOCKTOKEN=mocktoken')
        obj.save()

    @classmethod
    def setUpTestData(cls):
        cls.allup()

    def test_nameserver_str(self):
        for obj in models.NameServer.objects.all():
            self.assertEqual(str(obj), obj.__str__())

    def test_nameserver_serializer(self):
        obj = serializers.NameServerSerializer()
        json.loads(json.dumps(obj.to_representation(models.NameServer.objects.first())))


class DomainTestCase(AppTestCase):
    @classmethod
    def up(cls):
        # add mock domain
        ns = models.NameServer.objects.first()
        obj = models.Domain(name='example.com', nameserver=ns)
        obj.save()

    @classmethod
    def setUpTestData(cls):
        cls.allup()

    def test_domain_str(self):
        for obj in models.Domain.objects.all():
            self.assertEqual(str(obj), obj.__str__())

    def test_domain_api_positive(self):
        obj = models.Domain.objects.first()
        self.assertTrue(obj.api)

    def test_domain_api_negative_wihtout_ns(self):
        obj = models.Domain(name='example.com')
        self.assertFalse(obj.api)

    def test_domain_api_negative_without_ns_env(self):
        ns = models.NameServer(name='mocknameserver-2')
        ns.save()
        obj = models.Domain(name='example.com', nameserver=ns)
        self.assertFalse(obj.api)

    def test_domain_api_negative_with_empty_ns_env_key(self):
        ns = models.NameServer(name='mocknameserver-2', env='=')
        ns.save()
        origin = os.environ.copy()
        obj = models.Domain(name='example.com', nameserver=ns)
        # make sure os env is not massed up
        self.assertEqual(os.environ.copy(), origin)

    def test_domain_auto_resolve(self):
        obj = models.Domain(name='example.com')
        obj.auto_resolve()
        self.assertEqual(obj.name, 'example.com')

    def test_domain_auto_resolve(self):
        obj = models.Domain(name='www.example.com')
        obj.auto_resolve()
        self.assertEqual(obj.name, 'example.com')

    def test_domain_manager_get(self):
        obj = models.Domain.objects.get(name='www.example.com')
        self.assertEqual(obj.name, 'example.com')

    def test_domain_manager_filter(self):
        obj = models.Domain.objects.filter(name='www.example.com').first()
        self.assertEqual(obj.name, 'example.com')

    def test_domain_manager_get_or_create(self):
        obj, created = models.Domain.objects.get_or_create(name='www.example.com')
        self.assertEqual(obj.name, 'example.com')
        self.assertFalse(created)

    def test_domain_manager_update_or_create(self):
        obj, created = models.Domain.objects.update_or_create(name='www.example.com')
        self.assertEqual(obj.name, 'example.com')
        self.assertFalse(created)

    def test_domain_is_api_accessible_negative(self):
        for obj in models.Domain.objects.all():
            self.assertFalse(obj.is_api_accessible)

    def test_domain_serializer(self):
        obj = serializers.DomainSerializer()
        json.loads(json.dumps(obj.to_representation(models.Domain.objects.first())))


class RecordTestCase(AppTestCase):
    @classmethod
    def up(cls):
        # add mock record
        for domain in models.Domain.objects.all():
            obj = models.Record(host='vpn', domain=domain, type='A', answer='1.1.1.1')
            obj.save()

    @classmethod
    def setUpTestData(cls):
        cls.allup()

    def test_record_str(self):
        for obj in models.Record.objects.all():
            self.assertEqual(str(obj), obj.__str__())
    
    def test_record_init_with_fqdn(self):
        domain = models.Domain.objects.get(name='example.com')
        obj = models.Record(fqdn='vpn.example.com', type='A', answer='1.1.1.1')
        self.assertEqual(obj.domain, domain)
        self.assertEqual(obj.host, 'vpn')

    def test_record_site(self):
        site = models.Site.objects.get(pk=1)
        obj = models.Record(fqdn='www.example.com', type='A', answer='1.1.1.1', site=site)
        self.assertNotEqual(site.domain, obj.fqdn)
        obj.save()
        self.assertEqual(site.domain, obj.fqdn)

    def test_record_is_matching_dns_query_negative_noanwer(self):
        obj = models.Record(fqdn='nonexistinghost.example.com', type='A', answer='1.1.1.1')
        self.assertFalse(obj.is_matching_dns_query)

    def test_record_is_matching_dns_query_negative_wronganswer(self):
        obj = models.Record(fqdn='www.example.com', type='A', answer='1.1.1.1')
        self.assertFalse(obj.is_matching_dns_query)

    def test_record_is_matching_dns_query_positive(self):
        models.Domain(name='google.com').save()
        obj = models.Record(fqdn='dns.google.com', type='A', answer='8.8.8.8,8.8.4.4')
        self.assertTrue(obj.is_matching_dns_query)

    def test_record_on_update_anwser(self):
        obj = models.Record.objects.first()
        obj.answer = '2.2.2.2'
        result = json.loads(json.dumps(obj.on_update()))
        self.assertEqual(result['deleted'], {'origin': None})
        self.assertEqual(result['created'], {'null': ['2.2.2.2']})

    def test_record_on_update_host(self):
        obj = models.Record.objects.first()
        obj.host = 'new'
        result = json.loads(json.dumps(obj.on_update()))
        self.assertEqual(result['deleted'], {'origin': {}})
        self.assertEqual(result['created'], {'null': ['1.1.1.1']})

    def test_record_on_update_type(self):
        obj = models.Record.objects.first()
        obj.type = 'CNAME'
        obj.answer = 'new.example.com'
        result = json.loads(json.dumps(obj.on_update()))
        self.assertEqual(result['deleted'], {'origin': {}})
        self.assertEqual(result['created'], {'null': ['new.example.com']})

    def test_record_serializer(self):
        obj = serializers.RecordSerializer()
        json.loads(json.dumps(obj.to_representation(models.Record.objects.first())))


class ManagementCommandTestCase(AppTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.allup()

    def test_cmd_domain_domain_positive_root(self):
        call_command('domain_domain', '--name', 'example.org')
        self.assertTrue(models.Domain.objects.filter(name='example.org').exists())

    def test_cmd_domain_domain_positive_sub(self):
        call_command('domain_domain', '--name', 'www.example.org')
        self.assertTrue(models.Domain.objects.filter(name='example.org').exists())

    def test_cmd_domain_domain_with_nameserver_positive(self):
        call_command('domain_domain', '--name', 'example.org', '--nameserver', 'mocknameserver')
        self.assertTrue(models.Domain.objects.filter(name='example.org', nameserver__name='mocknameserver').exists())

        call_command('domain_domain', '--name', 'example.org', '--nameserver', '')
        self.assertTrue(models.Domain.objects.filter(name='example.org', nameserver=None).exists())

        call_command('domain_domain', '--name', 'example.org', '--nameserver', 'mocknameserver')
        self.assertTrue(models.Domain.objects.filter(name='example.org', nameserver__name='mocknameserver').exists())

        call_command('domain_domain', '--name', 'example.org')
        self.assertTrue(models.Domain.objects.filter(name='example.org', nameserver=None).exists())

    def test_cmd_domain_domain_with_nameserver_negative(self):
        self.assertRaises(models.NameServer.DoesNotExist, call_command, 'domain_domain', '--name', 'example.org', '--nameserver', 'mocknameserver-notexist')

    def test_cmd_domain_nameserver_positive(self):
        call_command('domain_nameserver', '--name', 'mocknameserver-2')
        self.assertTrue(models.NameServer.objects.filter(name='mocknameserver-2').exists())

        call_command('domain_nameserver', '--name', 'mocknameserver-2', '--env', 'KEY=VALUE')
        self.assertTrue(models.NameServer.objects.filter(name='mocknameserver-2', env='KEY=VALUE').exists())

        call_command('domain_nameserver', '--name', 'mocknameserver-2')
        self.assertTrue(models.NameServer.objects.filter(name='mocknameserver-2', env=None).exists())

        call_command('domain_nameserver', '--name', 'mocknameserver-2', '--env')
        self.assertTrue(models.NameServer.objects.filter(name='mocknameserver-2', env=None).exists())

        call_command('domain_nameserver', '--name', 'mocknameserver-2', '--env', '')
        self.assertTrue(models.NameServer.objects.filter(name='mocknameserver-2', env='').exists())

    def test_cmd_domain_record_positive_with_fqdn(self):
        call_command('domain_record', '--fqdn', 'www.example.com', '--type', 'A', '--answer', '1.1.1.1')
        self.assertTrue(models.Record.objects.filter(fqdn='www.example.com', type='A', answer='1.1.1.1').exists())

    def test_cmd_domain_record_positive_with_host_domain(self):
        call_command('domain_record', '--host', 'www', '--domain', 'example.com', '--type', 'A', '--answer', '1.1.1.1')
        self.assertTrue(models.Record.objects.filter(fqdn='www.example.com', type='A', answer='1.1.1.1').exists())

    def test_cmd_domain_record_positive_with_fqdn_host_domain(self):
        call_command('domain_record', '--fqdn', 'foo.example.com', '--host', 'bar', '--domain', 'example.com', '--type', 'A', '--answer', '1.1.1.1')
        self.assertTrue(models.Record.objects.filter(fqdn='bar.example.com', type='A', answer='1.1.1.1').exists())

        call_command('domain_record', '--fqdn', 'foo.example.com', '--host', 'bar', '--type', 'A', '--answer', '1.1.1.1')
        self.assertTrue(models.Record.objects.filter(fqdn='foo.example.com', type='A', answer='1.1.1.1').exists())

        call_command('domain_record', '--fqdn', 'foo.example.com', '--domain', 'example.org', '--type', 'A', '--answer', '1.1.1.1')
        self.assertTrue(models.Record.objects.filter(fqdn='foo.example.com', type='A', answer='1.1.1.1').exists())

    def test_cmd_domain_record_positive_with_site(self):
        call_command('domain_record', '--fqdn', 'www.example.com', '--type', 'A', '--answer', '1.1.1.1', '--site')
        self.assertTrue(models.Record.objects.filter(fqdn='www.example.com', type='A', answer='1.1.1.1', site__pk=models.settings.SITE_ID).exists())

    def test_cmd_domain_record_negative(self):
        self.assertRaises(models.Domain.DoesNotExist, call_command, 'domain_record', '--fqdn', 'www.example.org', '--type', 'A', '--answer', '1.1.1.1')

    def test_cmd_domain_site_positive(self):
        call_command('domain_site', '--name', 'example-org', '--domain', 'example.org')
        self.assertTrue(models.Site.objects.filter(name='example-org', domain='example.org').exists())

        call_command('domain_site', '--name', 'example-org')
        self.assertTrue(models.Site.objects.filter(name='example-org', domain='example.org').exists())

        call_command('domain_site', '--name', 'example-org', '--domain')
        self.assertTrue(models.Site.objects.filter(name='example-org', domain='example.org').exists())

        call_command('domain_site', '--name', 'example-org', '--domain', '')
        self.assertTrue(models.Site.objects.filter(name='example-org', domain='').exists())

        call_command('domain_site', '--domain', 'example.org')
        self.assertTrue(models.Site.objects.filter(name='example-org', domain='example.org').exists())

        call_command('domain_site', '--domain', 'example.org', '--name')
        self.assertTrue(models.Site.objects.filter(name='example-org', domain='example.org').exists())

        call_command('domain_site', '--domain', 'example.org', '--name', '')
        self.assertTrue(models.Site.objects.filter(name='', domain='example.org').exists())
