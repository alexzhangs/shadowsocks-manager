from rest_framework import serializers

import models


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
        fields = ('id', 'host', 'domain', 'type', 'answer', 'dt_created', 'dt_updated')
