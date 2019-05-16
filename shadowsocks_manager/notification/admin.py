# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from .models import Config, Template


# Register your models here.

@admin.register(Config)
class ConfigAdmin(admin.ModelAdmin):
    actions = None
    fields = ('sender_name', 'sender_email', 'dt_created', 'dt_updated')
    readonly_fields = ('dt_created', 'dt_updated')
    list_display = ('sender_name', 'sender_email', 'dt_created', 'dt_updated')

    def has_add_permission(self, request):
        return None

    def has_delete_permission(self, request, obj=None):
        return None


@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    fields = ('type', 'content', 'is_active', 'dt_created', 'dt_updated')
    readonly_fields = ('dt_created', 'dt_updated')
    list_display = ('type', 'content', 'is_active', 'dt_created', 'dt_updated')

