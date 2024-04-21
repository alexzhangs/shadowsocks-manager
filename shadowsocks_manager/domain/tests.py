# -*- coding: utf-8 -*-

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals
from __future__ import absolute_import

import json
from abc import abstractmethod
from django.test import TestCase

from domain import models, serializers


import logging
# disable logging for the test module to make the output clean
logging.disable(logging.CRITICAL)


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
    fixtures = ['nameserver.json']
    testcases = ['NameServerTestCase', 'DomainTestCase', 'RecordTestCase']


class NameServerTestCase(AppTestCase):
    @classmethod
    def up(cls):
        # add mock username and credential to nameserver
        for obj in models.NameServer.objects.all():
            if not obj.user:
                obj.user = 'mock-user'
            if not obj.credential:
                obj.credential = 'mock-credential'
            obj.save()

    @classmethod
    def setUpTestData(cls):
        cls.allup()

    def test_nameserver_is_api_accessible_negative(self):
        for obj in models.NameServer.objects.all():
            self.assertFalse(obj.is_api_accessible)

    def test_nameserver_serializer(self):
        obj = serializers.NameServerSerializer()
        json.loads(json.dumps(obj.to_representation(models.NameServer.objects.first())))


class DomainTestCase(AppTestCase):
    @classmethod
    def up(cls):
        # add mock domain
        for ns in models.NameServer.objects.all():
            obj = models.Domain(name='mock-example-{}.com'.format(ns.pk), nameserver=ns)
            obj.save()

    @classmethod
    def setUpTestData(cls):
        cls.allup()

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

    def test_record_is_matching_dns_query_negative(self):
        for obj in models.Record.objects.all():
            self.assertFalse(obj.is_matching_dns_query)

    def test_record_serializer(self):
        obj = serializers.RecordSerializer()
        json.loads(json.dumps(obj.to_representation(models.Record.objects.first())))
