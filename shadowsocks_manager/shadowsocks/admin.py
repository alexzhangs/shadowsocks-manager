# -*- coding: utf-8 -*-

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals

from django.contrib import admin, messages
from django.template.defaultfilters import filesizeformat
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from .models import Config, Node, Account, NodeAccount, SSManager


# Register your models here.

@admin.register(Config)
class ConfigAdmin(admin.ModelAdmin):
    actions = None
    fields = ('port_begin', 'port_end', 'timeout_remote', 'timeout_local', 'cache_timeout', 'dt_created', 'dt_updated')
    readonly_fields = ('dt_created', 'dt_updated')
    list_display = fields

    def has_add_permission(self, request, obj=None):
        return None

    def has_delete_permission(self, request, obj=None):
        return None


class ReadonlyNodeAccountInline(admin.TabularInline):
    model = NodeAccount
    extra = 1
    readonly_fields = ('is_created', 'is_accessible_ex', 'transferred_totally',
                       'dt_collected', 'dt_created', 'dt_updated')
    fields = ('node', 'account',) + readonly_fields + ('is_active',)

    def is_accessible_ex(self, obj):
        return obj.is_accessible_ex()

    is_accessible_ex.boolean = True
    is_accessible_ex.short_description = 'Is Accessible'

    def transferred_totally(self, obj):
        return filesizeformat(obj.transferred_totally)

    transferred_totally.short_description = 'Transferred'

    def dt_collected(self, obj):
        return obj.dt_collected

    dt_collected.short_description = 'Collected'


class SSManagerInline(admin.TabularInline):
    model = SSManager
    extra = 1
    max_num = 1

    fields = ('interface', 'port', 'encrypt', 'timeout', 'fastopen', 'is_accessible',
              'server_edition', 'is_v2ray_enabled', 'server_version', 'is_server_enabled', 'server_status',)
    readonly_fields = ('is_accessible', 'is_v2ray_enabled', 'server_version', 'server_status', 'dt_created', 'dt_updated')

    def is_accessible(self, obj):
        return obj.is_accessible

    is_accessible.boolean = True

    def server_version(self, obj):
        return obj.server.version

    def server_status(self, obj):
        return obj.server.status


@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):
    readonly_fields = ('transferred_totally', 'dt_collected', 'dt_created', 'dt_updated')
    fields = ('name', 'record', 'public_ip', 'private_ip', 'is_active', 'location',)
    list_display = fields + ('is_matching_dns_query',) + readonly_fields
    fields = fields + ('sns_endpoint', 'sns_access_key', 'sns_secret_key',) + readonly_fields

    def is_matching_dns_query(self, obj):
        return obj.is_matching_dns_query

    is_matching_dns_query.boolean = True
    is_matching_dns_query.short_description = 'DNS Query'

    def transferred_totally(self, obj):
        return filesizeformat(obj.transferred_totally)

    transferred_totally.short_description = 'Transferred'

    def dt_collected(self, obj):
        return obj.dt_collected

    dt_collected.short_description = 'Collected'

    inlines = [
        SSManagerInline,
        ReadonlyNodeAccountInline,
    ]

    exclude = ('node',)

    def toggle_active(self, request, queryset):
        for obj in queryset:
            obj.toggle_active()
            messages.info(request, '{}: now is {}'.format(obj, 'Active' if obj.is_active else 'Inactive'))

    toggle_active.short_description = 'Toggle Active/Inactive for Selected Shadowsocks Nodes'

    def change_ip(self, request, queryset):
        for obj in queryset:
            try:
                obj.change_ip()
            except Exception as e:
                messages.error(request, '{}: {}'.format(obj, e))
                return

            message = 'The message is sent to the SNS topic to request a new IP address.'
            messages.info(request, '{}: {}'.format(obj, message))

    change_ip.short_description = 'Replace the IP address with a new one for Selected Shadowsocks Nodes'

    actions = (toggle_active, change_ip)


class AccountResource(resources.ModelResource):

    class Meta:
        model = Account
        fields = ('id', 'username', 'password', 'email', 'first_name', 'last_name', 'date_joined',)
        export_order = ('username',)


@admin.register(Account)
class AccountAdmin(ImportExportModelAdmin):
    readonly_fields = ('transferred_totally', 'dt_collected', 'date_joined', 'dt_updated')
    fields = ('first_name', 'last_name', 'email', 'is_active',) + readonly_fields
    list_display = ('username',) + fields + readonly_fields
    fields = ('username', 'password',) + fields
    readonly_fields = ('groups',) + readonly_fields

    def transferred_totally(self, obj):
        return filesizeformat(obj.transferred_totally)

    transferred_totally.short_description = 'Transferred'

    def dt_collected(self, obj):
        return obj.dt_collected

    dt_collected.short_description = 'Collected'

    inlines = [
        ReadonlyNodeAccountInline,
    ]

    exclude = ('account',)

    def notify(self, request, queryset):
        for obj in queryset:
            try:
                to = '{}<{}>'.format(obj.get_full_name(), obj.email)
                if obj.notify(sender=request.user):
                    messages.info(request, '{}: Message queued for {}.'.format(obj, to))
                else:
                    messages.error(request, '{}: Message not queued for {}.'.format(obj, to))
            except Exception as e:
                messages.error(request, '{}: {}'.format(obj, e))

    notify.short_description = 'Send Notification Email to Selected Shadowsocks Accounts'

    def toggle_active(self, request, queryset):
        for obj in queryset:
            obj.toggle_active()
            messages.info(request, '{}: now is {}'.format(obj, 'Active' if obj.is_active else 'Inactive'))

    toggle_active.short_description = 'Toggle Active/Inactive for Selected Shadowsocks Accounts'

    def add_all_nodes(self, request, queryset):
        for obj in queryset:
            nodes = obj.add_all_nodes()
            messages.info(request, '{}: Added {}'.format(obj, nodes))

    add_all_nodes.short_description = 'Add All Nodes to Selected Shadowsocks Accounts'

    actions = (toggle_active, notify, add_all_nodes,)
    resource_class = AccountResource
