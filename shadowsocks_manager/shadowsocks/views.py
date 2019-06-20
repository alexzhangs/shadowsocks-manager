# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from rest_framework import viewsets

import models, serializers


# Create your views here.

class ConfigViewSet(viewsets.ModelViewSet):
    """
    This viewset automatically provides `list` and `detail` actions.
    """
    queryset = models.Config.objects.all()
    serializer_class = serializers.ConfigSerializer


class AccountViewSet(viewsets.ModelViewSet):
    """
    This viewset automatically provides `list` and `detail` actions.
    """
    queryset = models.Account.objects.all()
    serializer_class = serializers.AccountSerializer


class NodeViewSet(viewsets.ModelViewSet):
    """
    This viewset automatically provides `list` and `detail` actions.
    """
    queryset = models.Node.objects.all()
    serializer_class = serializers.NodeSerializer


class NodeAccountViewSet(viewsets.ModelViewSet):
    """
    This viewset automatically provides `list` and `detail` actions.
    """
    queryset = models.NodeAccount.objects.all()
    serializer_class = serializers.NodeAccountSerializer


class SSManagerViewSet(viewsets.ModelViewSet):
    """
    This viewset automatically provides `list` and `detail` actions.
    """
    queryset = models.SSManager.objects.all()
    serializer_class = serializers.SSManagerSerializer
