# py2.7 and py3 compatibility imports
from __future__ import absolute_import
from __future__ import unicode_literals

from rest_framework import serializers

from . import models


class TemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Template
        fields = ('id', 'type', 'content', 'is_active', 'dt_created', 'dt_updated')
