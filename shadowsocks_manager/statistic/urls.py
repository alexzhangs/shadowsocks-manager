# py2.7 and py3 compatibility imports
from __future__ import unicode_literals

from django.conf.urls import url, include
from rest_framework import routers

from . import views


router = routers.DefaultRouter()
router.register(r'statistic', views.StatisticViewSet)
router.register(r'statistic/period', views.PeriodViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
]
