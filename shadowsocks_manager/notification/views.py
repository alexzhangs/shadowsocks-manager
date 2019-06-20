# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from rest_framework import viewsets

import models, serializers


# Create your views here.

class TemplateViewSet(viewsets.ModelViewSet):
    """
    This viewset automatically provides `list` and `detail` actions.
    """
    queryset = models.Template.objects.all()
    serializer_class = serializers.TemplateSerializer
