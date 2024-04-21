# -*- coding: utf-8 -*-

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals
from __future__ import absolute_import

import json
from abc import abstractmethod
from django.test import TestCase

from shadowsocksz.tests import AppTestCase as ShadowsockszAppTestCase
from statistic import models, serializers


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
    fixtures = ShadowsockszAppTestCase.fixtures
    testcases = []


class PeriodTestCase(AppTestCase):
    def test_period_serializer(self):
        obj = serializers.PeriodSerializer()
        json.loads(json.dumps(obj.to_representation(models.Period.objects.first())))


class StatisticTestCase(AppTestCase):
    @classmethod
    def setUpTestData(cls):
        ShadowsockszAppTestCase.allup()

    def test_statistic_statistic(self):
        # no statistics data is asserted, cause there's no Manager API really called.
        models.Statistic.statistic()

        obj = serializers.StatisticSerializer()
        json.loads(json.dumps(obj.to_representation(models.Statistic.objects.first())))

    def test_statistic_reset(self):
        models.Statistic.reset()
