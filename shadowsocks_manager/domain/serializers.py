# py2.7 and py3 compatibility imports
from __future__ import absolute_import
from __future__ import unicode_literals

from rest_framework import serializers

from . import models


class NameServerSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.NameServer
        fields = ('id', 'name', 'env', 'dt_created', 'dt_updated')


class DomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Domain
        fields = ('id', 'name', 'nameserver', 'dt_created', 'dt_updated')


class RecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Record
        fields = ('id', 'fqdn', 'host', 'domain', 'type', 'answer', 'site', 'dt_created', 'dt_updated')
        extra_kwargs = {
            'fqdn': {'required': False, 'allow_null': True, 'default': None},
            'host': {'required': False, 'allow_null': True, 'default': None},
            'domain': {'required': False, 'allow_null': True, 'default': None},
        }
