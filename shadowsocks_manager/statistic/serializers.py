# py2.7 and py3 compatibility imports
from __future__ import unicode_literals

from rest_framework import serializers

from . import models


class PeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Period
        fields = ('id', 'year', 'month', 'dt_created', 'dt_updated')


class StatisticSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Statistic
        fields = ('id', 'period', 'content_type', 'object_id', 'transferred_past',
            'transferred_live', 'dt_collected', 'dt_created', 'dt_updated')
