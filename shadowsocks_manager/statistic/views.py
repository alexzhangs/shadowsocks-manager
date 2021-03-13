# -*- coding: utf-8 -*-

# py2.7 and py3 compatibility imports
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


class StatisticViewSet(viewsets.ModelViewSet):
    """
    This viewset automatically provides `list` and `detail` actions.
    """
    queryset = models.Statistic.objects.all()
    serializer_class = serializers.StatisticSerializer
