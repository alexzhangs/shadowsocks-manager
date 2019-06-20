from django.conf.urls import url, include
from rest_framework import routers

import views


router = routers.DefaultRouter()
router.register(r'shadowsocks/config', views.ConfigViewSet)
router.register(r'shadowsocks/account', views.AccountViewSet)
router.register(r'shadowsocks/node', views.NodeViewSet)
router.register(r'shadowsocks/nodeaccount', views.NodeAccountViewSet)
router.register(r'shadowsocks/ssmanager', views.SSManagerViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
]
