# -*- coding: utf-8 -*-

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals
from __future__ import absolute_import

from django.test import TestCase

from . import models


# Create your tests here.
class TestData:
    fixtures = ['nameserver.json']

    @classmethod
    def all(cls):
        cls.nameserver()
        cls.domain()
        cls.record()

    @classmethod
    def nameserver(cls):
        for obj in models.NameServer.objects.all():
            if not obj.user:
                obj.user = 'mock-user'
            if not obj.credential:
                obj.credential = 'mock-credential'
            obj.save()

    @classmethod
    def domain(cls):
        for ns in models.NameServer.objects.all():
            obj = models.Domain(name='mock-example-{}.com'.format(ns.pk), nameserver=ns)
            obj.save()

    @classmethod
    def record(cls):
        for domain in models.Domain.objects.all():
            obj = models.Record(host='ss', domain=domain, type='A', answer='1.1.1.1')
            obj.save()


class DomainTestCase(TestCase):
    fixtures = TestData.fixtures

    @classmethod
    def setUpTestData(cls):
        TestData.all()

    def test_nameserver(self):
        for obj in models.NameServer.objects.all():
            self.assertTrue(str(obj))
            self.assertFalse(obj.is_api_accessible)

    def test_domain(self):
        for obj in models.Domain.objects.all():
            self.assertTrue(str(obj))

    def test_record(self):
        for obj in models.Record.objects.all():
            self.assertTrue(str(obj))
            self.assertFalse(obj.is_matching_dns_query)
            obj.delete()
