# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from django.contrib.auth.models import User, Group

from .models import Config, Node, Account, NodeAccount, MonthlyStatistics


# Register your models here.
@admin.register(Config)
class ConfigAdmin(admin.ModelAdmin):
    actions = None
    fields = ('port_begin', 'port_end', 'timeout', 'dt_created', 'dt_updated')
    readonly_fields = ('dt_created', 'dt_updated')
    list_display = ('port_begin', 'port_end', 'timeout', 'dt_created', 'dt_updated')

    def has_add_permission(self, request):
        return None

    def has_delete_permission(self, request, obj=None):
        return None


class ReadonlyNodeAccountInline(admin.TabularInline):
    model = NodeAccount
    extra = 0
    readonly_fields = ('node', 'account', 'is_created', 'is_accessable', 'transferred_totally', 'dt_created', 'dt_updated')

    def has_add_permission(self, request):
        return None

    def is_accessable(self, obj):
        return obj.is_accessable

    is_accessable.boolean = True


class NodeAccountInline(admin.TabularInline):
    model = NodeAccount
    extra = 1
    can_delete = False
    fields = ('node', 'account')

    def has_change_permission(self, request):
        return None


@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):
    fields = ('name', 'public_ip', ('manager_ip', 'manager_port'),
                  'is_active', 'domain', 'location',
                  ('encrypt', 'timeout', 'fastopen'),
                  'transferred_totally', 'dt_created', 'dt_updated')

    readonly_fields = ('transferred_totally', 'dt_created', 'dt_updated')

    list_display = ('name', 'public_ip', 'manager_ip', 'manager_port',
                        'is_active', 'is_manager_accessable', 'is_dns_record_correct',
                        'domain', 'location',
                        'encrypt', 'timeout', 'fastopen',
                        'transferred_totally', 'dt_created', 'dt_updated')

    def is_manager_accessable(self, obj):
        return obj.is_manager_accessable

    is_manager_accessable.boolean = True

    def is_dns_record_correct(self, obj):
        return obj.is_dns_record_correct

    is_dns_record_correct.boolean = True

    inlines = [
        ReadonlyNodeAccountInline,
        NodeAccountInline,
    ]

    exclude = ('node',)


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    fields = ('username', 'password', 'first_name', 'last_name', 'email', 'is_active',
                  'groups', 'transferred_totally', 'date_joined', 'date_updated')

    readonly_fields = ('groups', 'transferred_totally', 'date_joined', 'date_updated')

    list_display = ('username', 'first_name', 'last_name', 'email', 'is_active',
                        'transferred_totally', 'date_joined', 'date_updated')

    inlines = [
        ReadonlyNodeAccountInline,
        NodeAccountInline,
    ]

    exclude = ('account',)

    def notify(modeladmin, request, queryset):
        for obj in queryset:
            obj.notify()

    notify.short_description = 'Send Notification Email to Selected Shadowsocks Accounts'

    actions = (notify,)


@admin.register(MonthlyStatistics)
class MonthlyStatisticsAdmin(admin.ModelAdmin):
    readonly_fields = ('transferred_monthly',)

    list_display = ('year', 'month', 'transferred_monthly', 'content_object',
                    'dt_calculated')

