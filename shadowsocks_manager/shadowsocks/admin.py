# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin, messages
from django.contrib.auth.models import User, Group
from django.template.defaultfilters import filesizeformat
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from .models import Config, Node, Account, NodeAccount, SSManager


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
                  'transferred_totally', 'dt_collected', 'dt_created', 'dt_updated')

    readonly_fields = fields
    fields = fields + ('is_active',)

    def has_add_permission(self, request):
        return None

    def is_accessable(self, obj):
        return obj.is_accessable

    is_accessable.boolean = True

    def transferred_totally(self, obj):
        return filesizeformat(obj.transferred_totally)

    transferred_totally.short_description = 'Transferred'

    def dt_collected(self, obj):
        return obj.dt_collected

    dt_collected.short_description = 'Collected'


class NodeAccountInline(admin.TabularInline):
    model = NodeAccount
    extra = 1
    can_delete = False
    fields = ('node', 'account', 'is_active')

    def has_change_permission(self, request):
        return None


class SSManagerInline(admin.TabularInline):
    model = SSManager
    extra = 1
    max_num = 1
    can_delete = False

    fields = ('interface', 'port', ('encrypt', 'timeout', 'fastopen'),
                  'is_accessable', 'dt_created', 'dt_updated')

    readonly_fields = ('is_accessable', 'dt_created', 'dt_updated')

    def is_accessable(self, obj):
        return obj.is_accessable

    is_accessable.boolean = True


@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):
    fields = ('name', 'domain', 'public_ip', 'private_ip', 'is_active', 'location',
                  'transferred_totally', 'dt_collected',
                  'dt_created', 'dt_updated')

    readonly_fields = ('transferred_totally', 'dt_collected', 'dt_created', 'dt_updated')

    list_display = ('name', 'domain', 'public_ip', 'private_ip',
                        'is_active', 'is_dns_record_correct',
                        'location',
                        'transferred_totally', 'dt_collected',
                        'dt_created', 'dt_updated')

    def is_dns_record_correct(self, obj):
        return obj.is_dns_record_correct

    is_dns_record_correct.boolean = True
    is_dns_record_correct.short_description = 'DNS'

    def transferred_totally(self, obj):
        return filesizeformat(obj.transferred_totally)

    transferred_totally.short_description = 'Transferred'

    def dt_collected(self, obj):
        return obj.dt_collected

    dt_collected.short_description = 'Collected'

    inlines = [
        SSManagerInline,
        ReadonlyNodeAccountInline,
        NodeAccountInline,
    ]

    exclude = ('node',)

    def toggle_active(self, request, queryset):
        for obj in queryset:
            obj.toggle_active()
            messages.info(request, '{cls} {obj} now is {status}'.format(
                cls=obj.__class__.__name__,
                obj=obj,
                status=('Active' if obj.is_active else 'Inactive')))

    toggle_active.short_description = 'Toggle Active/Inactive for Selected Shadowsocks Nodes'

    actions = (toggle_active,)


class AccountResource(resources.ModelResource):
    
    class Meta:
        model = Account
        fields = ('id', 'username', 'password', 'email', 'first_name', 'last_name', 'date_joined',)
        export_order = ('username',)


@admin.register(Account)
class AccountAdmin(ImportExportModelAdmin):
    fields = ('username', 'password', 'first_name', 'last_name', 'email', 'is_active',
                  'groups', 'transferred_totally', 'dt_collected', 'date_joined', 'dt_updated')

    readonly_fields = ('groups', 'transferred_totally', 'dt_collected', 'date_joined', 'dt_updated')

    list_display = ('username', 'first_name', 'last_name', 'email', 'is_active',
                        'transferred_totally', 'dt_collected', 'date_joined', 'dt_updated')

    def transferred_totally(self, obj):
        return filesizeformat(obj.transferred_totally)

    transferred_totally.short_description = 'Transferred'

    def dt_collected(self, obj):
        return obj.dt_collected

    dt_collected.short_description = 'Collected'

    inlines = [
        ReadonlyNodeAccountInline,
        NodeAccountInline,
    ]

    exclude = ('account',)

    def notify(self, request, queryset):
        for obj in queryset:
            to = '{}<{}>'.format(obj.get_full_name(), obj.email)
            try:
                if obj.notify(sender=request.user):
                    messages.info(request, 'Message queued for {}'.format(to))
                else:
                    messages.error(request, 'Message not queued for {}'.format(to))
            except Exception as e:
                messages.error(request, e)

    notify.short_description = 'Send Notification Email to Selected Shadowsocks Accounts'

    def toggle_active(self, request, queryset):
        for obj in queryset:
            obj.toggle_active()
            messages.info(request, '{cls} {obj} now is {status}'.format(
                cls=obj.__class__.__name__,
                obj=obj,
                status=('Active' if obj.is_active else 'Inactive')))

    toggle_active.short_description = 'Toggle Active/Inactive for Selected Shadowsocks Accounts'

    actions = (toggle_active, notify,)
    resource_class = AccountResource
