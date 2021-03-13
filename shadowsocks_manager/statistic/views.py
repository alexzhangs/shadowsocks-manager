# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from rest_framework import viewsets

from . import models, serializers


# Create your views here.

class PeriodViewSet(viewsets.ModelViewSet):
    """
    This viewset automatically provides `list` and `detail` actions.
    """
    queryset = models.Period.objects.all()
    serializer_class = serializers.PeriodSerializer


class StatisticsViewSet(viewsets.ModelViewSet):
    """
    This viewset automatically provides `list` and `detail` actions.
    """
    queryset = models.Statistic.objects.all()
    serializer_class = serializers.StatisticsSerializer
