from rest_framework import serializers

import models


class DomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Domain
        fields = ('id', 'name', 'nameserver', 'user', 'credential', 'dt_created', 'dt_updated')
