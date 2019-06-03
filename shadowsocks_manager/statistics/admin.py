# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin, messages
from django.utils.translation import ugettext_lazy as _

from .models import Period, Statistics


# Register your models here.

class TermListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _('term')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'term'

    def lookups(self, request, model_admin):
        valid_term = Period.valid_term
        return map(
            None,
            valid_term,
            [_(item) for item in valid_term]
        )

    def queryset(self, request, queryset):
        if self.value():
            q_ids = [item.pk for item in queryset if item.period.term == self.value()]
            return queryset.filter(id__in=q_ids)
        else:
            return queryset


class ContentTypeListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _('content type')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'contenttype'

    def lookups(self, request, model_admin):
        valid_cls = Statistics.valid_cls
        return map(
            None,
            [item.__name__.lower() for item in valid_cls],
            [item._meta.verbose_name for item in valid_cls]
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(content_type__model=self.value())
        else:
            return queryset


@admin.register(Statistics)
class StatisticsAdmin(admin.ModelAdmin):
    list_display = ('period', 'content_object', 'object_type', 'transferred',
                    'dt_collected', )
    fields = ('content_type', 'object_id')  + list_display + ('transferred_past', 'transferred_live', 'dt_created', 'dt_updated')
    list_filter = (TermListFilter, 'period', ContentTypeListFilter,)
    readonly_fields = fields
