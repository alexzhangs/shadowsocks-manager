# -*- coding: utf-8 -*-

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals
from __future__ import absolute_import

import json
from django.test import TestCase

from domain import models, serializers


# Create your tests here.
class DomainTestCase(TestCase):
    fixtures = ['nameserver.json']

    @classmethod
    def up(cls):
        print('Domain.NameServer: loading data ...')
        for obj in models.NameServer.objects.all():
            if not obj.user:
                obj.user = 'mock-user'
            if not obj.credential:
                obj.credential = 'mock-credential'
            obj.save()

        print('Domain.Domain: loading data ...')
        for ns in models.NameServer.objects.all():
            obj = models.Domain(name='mock-example-{}.com'.format(ns.pk), nameserver=ns)
            obj.save()

        print('Domain.Record: loading data ...')
        for domain in models.Domain.objects.all():
            obj = models.Record(host='ss', domain=domain, type='A', answer='1.1.1.1')
            obj.save()

    @classmethod
    def down(cls):
        print('Domain: tearing down ...')
        pass

    @classmethod
    def setUpTestData(cls):
        cls.up()

    def test_nameserver(self):
        for obj in models.NameServer.objects.all():
            self.assertTrue(str(obj))
            self.assertFalse(obj.is_api_accessible)

        obj = serializers.NameServerSerializer()
        json.loads(json.dumps(obj.to_representation(models.NameServer.objects.first())))

    def test_domain(self):
        for obj in models.Domain.objects.all():
            self.assertTrue(str(obj))

        obj = serializers.DomainSerializer()
        json.loads(json.dumps(obj.to_representation(models.Domain.objects.first())))

    def test_record(self):
        obj = serializers.RecordSerializer()
        json.loads(json.dumps(obj.to_representation(models.Record.objects.first())))

        for obj in models.Record.objects.all():
            self.assertTrue(str(obj))
            self.assertFalse(obj.is_matching_dns_query)
            obj.delete()
