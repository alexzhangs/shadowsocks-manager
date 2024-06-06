# -*- coding: utf-8 -*-

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals

import json
from django.contrib import admin, messages
from admin_lazy_load import LazyLoadAdminMixin

from .models import NameServer, Domain, Record


# Register your models here.

@admin.register(NameServer)
class NameServerAdmin(admin.ModelAdmin):
    fields = ('name', 'env',
                  'dt_created', 'dt_updated')

    readonly_fields = ('dt_created', 'dt_updated')

    list_display = ('name', 'env',
                        'dt_created', 'dt_updated')


@admin.register(Domain)
class DomainAdmin(LazyLoadAdminMixin, admin.ModelAdmin):
    fields = ('name', 'nameserver',
                  'dt_created', 'dt_updated')

    readonly_fields = ('dt_created', 'dt_updated')

    list_display = ('name', 'nameserver', 'is_api_accessible_lazy',
                        'dt_created', 'dt_updated')
    
    lazy_loaded_fields = ('is_api_accessible',)

    def is_api_accessible(self, obj):
        return obj.is_api_accessible

    is_api_accessible.boolean = True
    is_api_accessible.short_description = 'API'


@admin.register(Record)
class RecordAdmin(LazyLoadAdminMixin, admin.ModelAdmin):
    fields = ('host', 'domain', 'type', 'answer', 'site',
                  'dt_created', 'dt_updated')

    readonly_fields = ('dt_created', 'dt_updated')

    list_display = ('host', 'domain', 'type', 'answer', 'answer_from_dns_api_lazy', 'is_matching_dns_api_lazy',
                        'answer_from_dns_query_lazy', 'is_matching_dns_query_lazy', 'site',
                        'dt_created', 'dt_updated')
    
    lazy_loaded_fields = ('answer_from_dns_api', 'answer_from_dns_query',
                          'is_matching_dns_api', 'is_matching_dns_query')

    def answer_from_dns_api(self, obj):
        return list(obj.answer_from_dns_api or [])

    def answer_from_dns_query(self, obj):
        return list(obj.answer_from_dns_query or [])

    def is_matching_dns_api(self, obj):
        return obj.is_matching_dns_api

    is_matching_dns_api.boolean = True
    is_matching_dns_api.short_description = 'DNS API'

    def is_matching_dns_query(self, obj):
        return obj.is_matching_dns_query

    is_matching_dns_query.boolean = True
    is_matching_dns_query.short_description = 'DNS Query'

    def dns_sync(self, request, queryset):
        for obj in queryset:
            result = obj.dns_sync()
            messages.info(request, '{0}: {1}'.format(obj.fqdn, json.dumps(result)))

    dns_sync.short_description = 'Synchronize DNS records to DNS server for Selected Domain'

    actions = (dns_sync,)
