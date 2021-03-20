# -*- coding: utf-8 -*-

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals
from __future__ import absolute_import

from shadowsocks.tests import TestData as ShadowsocksTestData
from . import models

from django.test import TestCase

# Create your tests here.
class TestData:
    fixtures = []

    @classmethod
    def all(cls):
        cls.period()
        cls.statistic()

    @classmethod
    def period(cls):
        pass

    @classmethod
    def statistic(cls):
        pass


class ConfigTestCase(TestCase):
    fixtures = TestData.fixtures
    fixtures.extend(ShadowsocksTestData.fixtures)

    def setUp(self):
        TestData.all()
        ShadowsocksTestData.all()

    def test(self):
        # no statistics data is asserted, cause there's no Manager API really called.
        models.Statistic.statistic()
        models.Statistic.reset()
