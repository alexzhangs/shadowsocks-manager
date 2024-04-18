# -*- coding: utf-8 -*-

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals
from __future__ import absolute_import

import json
from django.test import TestCase

from shadowsocksz.tests import AllData as ShadowsocksTestData
from statistic import models, serializers

# Create your tests here.
class PeriodTestCase(TestCase):

    def test(self):
        obj = serializers.PeriodSerializer()
        json.loads(json.dumps(obj.to_representation(models.Period.objects.first())))


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

        obj = serializers.StatisticSerializer()
        json.loads(json.dumps(obj.to_representation(models.Statistic.objects.first())))
