# -*- coding: utf-8 -*-

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals
from __future__ import absolute_import

from utils.viewsets import CompatModelViewSet

from . import models, serializers


# Create your views here.

class TemplateViewSet(CompatModelViewSet):
    """
    This viewset automatically provides `list` and `detail` actions.
    """
    queryset = models.Template.objects.all()
    serializer_class = serializers.TemplateSerializer
