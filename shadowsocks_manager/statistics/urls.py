from django.conf.urls import url, include
from rest_framework import routers

import views


router = routers.DefaultRouter()
router.register(r'statistics', views.StatisticsViewSet)
router.register(r'statistics/period', views.PeriodViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
]
