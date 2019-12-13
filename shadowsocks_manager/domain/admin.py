# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
from django.contrib import admin, messages

from .models import Domain


# Register your models here.

@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    fields = ('name', 'nameserver', 'user', 'credential',
                  'dt_created', 'dt_updated')

    readonly_fields = ('dt_created', 'dt_updated')

    list_display = ('name', 'nameserver', 'user', 'is_manager_accessable', 'active_dns_records', 'active_nodes',
                        'dt_created', 'dt_updated')

    def is_manager_accessable(self, obj):
        return obj.is_manager_accessable

    is_manager_accessable.boolean = True
    is_manager_accessable.short_description = 'Manager'

    def active_dns_records(self, obj):
        return obj.active_dns_records

    def active_nodes(self, obj):
        return obj.active_nodes

    def sync(self, request, queryset):
        for obj in queryset:
            result = obj.sync()
            messages.info(request, '{0}: {1}'.format(obj.name, json.dumps(result)))

    sync.short_description = 'Synchronize DNS records for Selected Domain'

    actions = (sync,)

