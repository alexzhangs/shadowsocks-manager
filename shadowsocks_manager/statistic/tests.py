# -*- coding: utf-8 -*-

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals
from __future__ import absolute_import

from shadowsocks.tests import AllData as ShadowsocksTestData
from . import models

from django.test import TestCase

# Create your tests here.
class StatisticTestCase(TestCase):
    fixtures = []
    fixtures.extend(ShadowsocksTestData.fixtures)

    def setUp(self):
        ShadowsocksTestData.up()

    def tearDown(self):
        ShadowsocksTestData.down()

    def test(self):
        # no statistics data is asserted, cause there's no Manager API really called.
        models.Statistic.statistic()
        models.Statistic.reset()
