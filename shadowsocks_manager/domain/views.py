# -*- coding: utf-8 -*-

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals
from __future__ import absolute_import

import django_filters

from utils.viewsets import CompatModelViewSet

from . import models, serializers


# Create your views here.

class NameServerViewSet(CompatModelViewSet):
    """
    This viewset automatically provides `list` and `detail` actions.
    """
    queryset = models.NameServer.objects.all()
    serializer_class = serializers.NameServerSerializer
    filter_fields = ['name', 'env']


class CustomDomainFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(method='filter_by_name')

    class Meta:
        model = models.Domain
        fields = ['name', 'nameserver', 'nameserver__name']

    def filter_by_name(self, queryset, name, value):
        zone = models.get_zone_name(value)
        return queryset.filter(name=zone)

class DomainViewSet(CompatModelViewSet):
    """
    This viewset automatically provides `list` and `detail` actions.
    """
    queryset = models.Domain.objects.all()
    serializer_class = serializers.DomainSerializer
    filterset_class = CustomDomainFilter


class RecordViewSet(CompatModelViewSet):
    """
    This viewset automatically provides `list` and `detail` actions.
    """
    queryset = models.Record.objects.all()
    serializer_class = serializers.RecordSerializer
    filter_fields = ['fqdn', 'host', 'domain', 'domain__name', 'type', 'answer', 'site', 'site__name', 'site__domain']
