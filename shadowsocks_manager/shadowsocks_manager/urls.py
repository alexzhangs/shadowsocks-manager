"""shadowsocks_manager URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals

from django.conf.urls import url, include
from django.contrib import admin
from django.utils.safestring import mark_safe
from django.conf import settings


admin.site.site_title = "Shadowsocks Manager"
admin.site.site_header = mark_safe('Shadowsocks Manager Administration <span style="font-size: x-small">{}</span>'.format(settings.VERSION))
admin.site.index_title = "Administration"

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^', include('notification.urls')),
    url(r'^', include('shadowsocks.urls')),
    url(r'^', include('statistic.urls')),
    url(r'^', include('domain.urls')),
]
