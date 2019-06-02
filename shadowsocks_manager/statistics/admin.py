# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin, messages

from .models import Period, Statistics


# Register your models here.

@admin.register(Statistics)
class StatisticsAdmin(admin.ModelAdmin):
    list_display = ('period', 'content_object', 'object_type', 'transferred',
                    'dt_collected', )
    fields = ('content_type', 'object_id')  + list_display + ('transferred_past', 'transferred_live', 'dt_created', 'dt_updated')
    readonly_fields = fields
