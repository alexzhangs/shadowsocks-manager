# -*- coding: utf-8 -*-

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals
from __future__ import absolute_import

from rest_framework import viewsets

from . import models, serializers


# Create your views here.

class NameServerViewSet(viewsets.ModelViewSet):
    """
    This viewset automatically provides `list` and `detail` actions.
    """
    queryset = models.NameServer.objects.all()
    serializer_class = serializers.NameServerSerializer
    filter_fields = ['name', 'api_cls_name', 'user']


class DomainViewSet(viewsets.ModelViewSet):
    """
    This viewset automatically provides `list` and `detail` actions.
    """
    queryset = models.Domain.objects.all()
    serializer_class = serializers.DomainSerializer
    filter_fields = ['name', 'nameserver', 'nameserver__name']


class RecordViewSet(viewsets.ModelViewSet):
    """
    This viewset automatically provides `list` and `detail` actions.
    """
    queryset = models.Record.objects.all()
    serializer_class = serializers.RecordSerializer
    filter_fields = ['host', 'domain', 'domain__name', 'type', 'answer', 'site', 'site__name', 'site__domain']
