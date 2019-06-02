# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin, messages
from django.contrib.auth.models import User, Group

from .models import Config, Node, Account, NodeAccount


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
    fields = ('node', 'account', 'is_created', 'is_accessable',
                           'transferred', 'dt_collected', 'dt_created', 'dt_updated')

    readonly_fields = fields

    def has_add_permission(self, request):
        return None

    def is_accessable(self, obj):
        return obj.is_accessable

    is_accessable.boolean = True

    def transferred(self, obj):
        return obj.transferred

    def dt_collected(self, obj):
        return obj.dt_collected


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
                  'transferred', 'dt_collected',
                  ('encrypt', 'timeout', 'fastopen'),
                  'dt_created', 'dt_updated')

    readonly_fields = ('transferred', 'dt_collected', 'dt_created', 'dt_updated')

    list_display = ('name', 'public_ip', 'manager_ip', 'manager_port',
                        'is_active', 'is_manager_accessable', 'is_dns_record_correct',
                        'domain', 'location',
                        'transferred', 'dt_collected',
                        'encrypt', 'timeout', 'fastopen',
                        'dt_created', 'dt_updated')

    def is_manager_accessable(self, obj):
        return obj.is_manager_accessable

    is_manager_accessable.boolean = True
    is_manager_accessable.short_description = 'Manager'

    def is_dns_record_correct(self, obj):
        return obj.is_dns_record_correct

    is_dns_record_correct.boolean = True
    is_dns_record_correct.short_description = 'DNS'

    def transferred(self, obj):
        return obj.transferred

    def dt_collected(self, obj):
        return obj.dt_collected

    inlines = [
        ReadonlyNodeAccountInline,
        NodeAccountInline,
    ]

    exclude = ('node',)

    def toggle_active(self, request, queryset):
        for obj in queryset:
            obj.toggle_active()
            messages.info(request, '%s %s now is %s' % (obj.__class__.__name__, obj, ('Active' if obj.is_active else 'Inactive')))

    toggle_active.short_description = 'Toggle Active/Inactive for Selected Shadowsocks Nodes'

    actions = (toggle_active,)


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    fields = ('username', 'password', 'first_name', 'last_name', 'email', 'is_active',
                  'groups', 'transferred', 'dt_collected', 'date_joined', 'dt_updated')

    readonly_fields = ('groups', 'transferred', 'dt_collected', 'date_joined', 'dt_updated')

    list_display = ('username', 'first_name', 'last_name', 'email', 'is_active',
                        'transferred', 'dt_collected', 'date_joined', 'dt_updated')

    def transferred(self, obj):
        return obj.transferred

    def dt_collected(self, obj):
        return obj.dt_collected

    inlines = [
        ReadonlyNodeAccountInline,
        NodeAccountInline,
    ]

    exclude = ('account',)

    def notify(self, request, queryset):
        for obj in queryset:
            if obj.notify():
                messages.info(request, 'Message queued for %s(%s)' % (obj.email, obj.get_full_name()))
            else:
                messages.error(request, 'Message not queued for %s(%s)' % (obj.email, obj.get_full_name()))

    notify.short_description = 'Send Notification Email to Selected Shadowsocks Accounts'

    def toggle_active(self, request, queryset):
        for obj in queryset:
            obj.toggle_active()
            messages.info(request, '%s %s now is %s' % (obj.__class__.__name__, obj, ('Active' if obj.is_active else 'Inactive')))

    toggle_active.short_description = 'Toggle Active/Inactive for Selected Shadowsocks Accounts'

    actions = (toggle_active, notify,)
