# -*- coding: utf-8 -*-

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals

import json
from django.contrib import admin, messages

from .models import NameServer, Domain, Record


# Register your models here.

@admin.register(NameServer)
class NameServerAdmin(admin.ModelAdmin):
    fields = ('name', 'api_cls_name', 'user', 'credential',
                  'dt_created', 'dt_updated')

    readonly_fields = ('dt_created', 'dt_updated')

    list_display = ('name', 'api_cls_name', 'user', 'is_api_accessible',
                        'dt_created', 'dt_updated')

    def is_api_accessible(self, obj):
        return obj.is_api_accessible

    is_api_accessible.boolean = True
    is_api_accessible.short_description = 'API'


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    fields = ('name', 'nameserver',
                  'dt_created', 'dt_updated')

    readonly_fields = ('dt_created', 'dt_updated')

    list_display = ('name', 'nameserver',
                        'dt_created', 'dt_updated')


@admin.register(Record)
class RecordAdmin(admin.ModelAdmin):
    fields = ('host', 'domain', 'type', 'answer', 'site',
                  'dt_created', 'dt_updated')

    readonly_fields = ('dt_created', 'dt_updated')

    list_display = ('host', 'domain', 'type', 'answer', 'answer_from_dns_api', 'is_matching_dns_api',
                        'answer_from_dns_query', 'is_matching_dns_query', 'site',
                        'dt_created', 'dt_updated')

    def answer_from_dns_api(self, obj):
        return list(obj.answer_from_dns_api) if obj.answer_from_dns_api is not None else obj.answer_from_dns_api

    def answer_from_dns_query(self, obj):
        return list(obj.answer_from_dns_query) if obj.answer_from_dns_query is not None else obj.answer_from_dns_query

    def is_matching_dns_api(self, obj):
        return obj.is_matching_dns_api

    is_matching_dns_api.boolean = True
    is_matching_dns_api.short_description = 'DNS API'

    def is_matching_dns_query(self, obj):
        return obj.is_matching_dns_query

    is_matching_dns_query.boolean = True
    is_matching_dns_query.short_description = 'DNS Query'

    def sync_to_dns(self, request, queryset):
        for obj in queryset:
            result = obj.sync_to_dns()
            messages.info(request, '{0}: {1}'.format(obj.host, json.dumps(result)))

    sync_to_dns.short_description = 'Synchronize DNS records to DNS server for Selected Domain'

    actions = (sync_to_dns,)
