from rest_framework import serializers

import models


class ConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Config
        fields = ('id', 'port_begin', 'port_end', 'timeout', 'dt_created', 'dt_updated')


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Account
        fields = ('id', 'username', 'password', 'first_name', 'last_name', 'email', 'is_active', 'date_joined', 'dt_updated')


class NodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Node
        fields = ('id', 'name', 'domain', 'public_ip', 'private_ip', 'location', 'is_active', 'dt_created', 'dt_updated')


class NodeAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.NodeAccount
        fields = ('id', 'node', 'account', 'is_active', 'dt_created', 'dt_updated')


class SSManagerSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.SSManager
        fields = ('id', 'node', 'interface', 'port', 'encrypt', 'timeout', 'fastopen', 'dt_created', 'dt_updated')
