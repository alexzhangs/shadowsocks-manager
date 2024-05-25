# -*- coding: utf-8 -*-

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals

from utils.viewsets import CompatModelViewSet

from . import models, serializers


# Create your views here.

class PeriodViewSet(CompatModelViewSet):
    """
    This viewset automatically provides `list` and `detail` actions.
    """
    queryset = models.Period.objects.all()
    serializer_class = serializers.PeriodSerializer


class StatisticViewSet(CompatModelViewSet):
    """
    This viewset automatically provides `list` and `detail` actions.
    """
    queryset = models.Statistic.objects.all()
    serializer_class = serializers.StatisticSerializer
