# py2.7 and py3 compatibility imports
from __future__ import absolute_import
from __future__ import unicode_literals

from rest_framework import serializers

from . import models


class NameServerSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.NameServer
        fields = ('id', 'name', 'api_cls_name', 'user', 'credential', 'dt_created', 'dt_updated')


class DomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Domain
        fields = ('id', 'name', 'nameserver', 'dt_created', 'dt_updated')


class RecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Record
        fields = ('id', 'host', 'domain', 'type', 'answer', 'site', 'dt_created', 'dt_updated')
