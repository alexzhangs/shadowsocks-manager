from django.conf.urls import url, include
from rest_framework import routers

from . import views


router = routers.DefaultRouter()
router.register(r'statistic', views.StatisticsViewSet)
router.register(r'statistic/period', views.PeriodViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
]
