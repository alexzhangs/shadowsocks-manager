# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from django.contrib.auth.models import User, Group
from .models import Config, Node, Account, NodeAccount, MonthlyStatistics


# Register your models here.
@admin.register(Config)
class ConfigAdmin(admin.ModelAdmin):
    fields = ('port_begin', 'port_end', 'admin_name', 'admin_email',
                    'dt_created', 'dt_updated')

    readonly_fields = ('dt_created', 'dt_updated')

    list_display = ('port_begin', 'port_end', 'admin_name', 'admin_email',
                    'dt_created', 'dt_updated')


@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):
    fields = ('name', 'public_ip', ('manager_ip', 'manager_port'),
                  ('encrypt', 'timeout', 'fastopen'),
                  'domain', 'location', 'is_active',
                  'transferred_totally', 'dt_created', 'dt_updated')

    readonly_fields = ('transferred_totally', 'dt_created', 'dt_updated')

    list_display = ('name', 'public_ip', 'manager_ip',
                        'manager_port', 'encrypt', 'timeout', 'fastopen',
                        'domain', 'location', 'is_active',
                        'transferred_totally', 'dt_created', 'dt_updated')


class ReadonlyNodeAccountInline(admin.TabularInline):
    model = NodeAccount
    extra = 0
    readonly_fields = ('node', 'transferred_totally', 'dt_created', 'dt_updated',)

    def has_add_permission(self, request):
        return None


class NodeAccountInline(admin.TabularInline):
    model = NodeAccount
    extra = 1
    can_delete = False
    fields = ('node',)

    def has_change_permission(self, request):
        return None


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


@admin.register(MonthlyStatistics)
class MonthlyStatisticsAdmin(admin.ModelAdmin):
    readonly_fields = ('transferred_monthly',)

    list_display = ('year', 'month', 'transferred_monthly', 'content_object',
                    'dt_calculated')

