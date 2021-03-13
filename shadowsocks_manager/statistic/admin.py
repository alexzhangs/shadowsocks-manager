# -*- coding: utf-8 -*-

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals

from django.contrib import admin, messages
from django.utils.translation import ugettext_lazy as _
from django.template.defaultfilters import filesizeformat

from .models import Period, Statistic


# Register your models here.

class TermListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _('term')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'term'

    def lookups(self, request, model_admin):
        valid_term = Period.valid_term
        return zip(
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
        valid_cls = Statistic.valid_cls
        return zip(
            [item.__name__.lower() for item in valid_cls],
            [item._meta.verbose_name for item in valid_cls]
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(content_type__model=self.value())
        else:
            return queryset


@admin.register(Statistic)
class StatisticAdmin(admin.ModelAdmin):
    list_display = ('period', 'term', 'content_object', 'content_type', 'transferred', 'dt_collected', )
    list_filter = (TermListFilter, 'period', ContentTypeListFilter,)
    fields = list_display + ('transferred_past', 'transferred_live', 'dt_created', 'dt_updated')
    readonly_fields = fields
    ordering = ('-period', 'content_type', 'dt_collected')

    def term(self, obj):
        return obj.period.term

    def transferred(self, obj):
        return filesizeformat(obj.transferred)

    def transferred_past(self, obj):
        return filesizeformat(obj.transferred_past)

    def transferred_live(self, obj):
        return filesizeformat(obj.transferred_live)
