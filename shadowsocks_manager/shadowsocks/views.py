# -*- coding: utf-8 -*-

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals
from __future__ import absolute_import

from shadowsocks_manager.utils.viewsets import CompatModelViewSet

from . import models, serializers


# Create your views here.

class ConfigViewSet(CompatModelViewSet):
    """
    This viewset automatically provides `list` and `detail` actions.
    """
    queryset = models.Config.objects.all()
    serializer_class = serializers.ConfigSerializer


class AccountViewSet(CompatModelViewSet):
    """
    This viewset automatically provides `list` and `detail` actions.
    """
    queryset = models.Account.objects.all()
    serializer_class = serializers.AccountSerializer


class NodeViewSet(CompatModelViewSet):
    """
    This viewset automatically provides `list` and `detail` actions.
    """
    queryset = models.Node.objects.all()
    serializer_class = serializers.NodeSerializer
    filter_fields = ['name']


class NodeAccountViewSet(CompatModelViewSet):
    """
    This viewset automatically provides `list` and `detail` actions.
    """
    queryset = models.NodeAccount.objects.all()
    serializer_class = serializers.NodeAccountSerializer


class SSManagerViewSet(CompatModelViewSet):
    """
    This viewset automatically provides `list` and `detail` actions.
    """
    queryset = models.SSManager.objects.all()
    serializer_class = serializers.SSManagerSerializer
    filter_fields = ['node', 'node__name', 'server_edition', 'is_v2ray_enabled']
