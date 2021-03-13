# py2.7 and py3 compatibility imports
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import url, include
from rest_framework import routers

from . import views


router = routers.DefaultRouter()
router.register(r'domain/nameserver', views.NameServerViewSet)
router.register(r'domain/domain', views.DomainViewSet)
router.register(r'domain/record', views.RecordViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
]
