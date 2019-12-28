# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from rest_framework import viewsets

import models, serializers


# Create your views here.

class DomainViewSet(viewsets.ModelViewSet):
    """
    This viewset automatically provides `list` and `detail` actions.
    """
    queryset = models.Domain.objects.all()
    serializer_class = serializers.DomainSerializer
    filter_fields = ['name']
