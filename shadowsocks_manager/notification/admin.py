# -*- coding: utf-8 -*-

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals

from django.contrib import admin

from .models import Template


# Register your models here.

@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    fields = ('type', 'content', 'is_active', 'dt_created', 'dt_updated')
    readonly_fields = ('dt_created', 'dt_updated')
    list_display = ('type', 'content', 'is_active', 'dt_created', 'dt_updated')

