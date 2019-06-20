from rest_framework import serializers

import models


class TemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Template
        fields = ('id', 'type', 'content', 'is_active', 'dt_created', 'dt_updated')
