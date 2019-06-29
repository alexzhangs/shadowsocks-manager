from rest_framework import serializers

import models


class PeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Period
        fields = ('id', 'year', 'month', 'dt_created', 'dt_updated')


class StatisticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Statistics
        fields = ('id', 'period', 'content_type', 'object_id', 'transferred_past',
            'transferred_live', 'dt_collected', 'dt_created', 'dt_updated')