# -*- coding: utf-8 -*-

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals
from builtins import str

import logging
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django_lock import lock

from shadowsocksz.models import Node, Account, NodeAccount


logger = logging.getLogger('django')


# Create your models here.

class Period(models.Model):
    year = models.PositiveIntegerField(null=True, blank=True)
    month = models.PositiveIntegerField(null=True, blank=True)
    dt_created = models.DateTimeField('Created', auto_now_add=True)
    dt_updated = models.DateTimeField('Updated', auto_now=True)

    class Meta:
        verbose_name = 'Period'
        unique_together = ('year', 'month')

    def __str__(self):
        return str(self.year) + ('-' + str(self.month) if self.month else '') if self.year else 'Total'

    valid_term = ['Monthly', 'Yearly', 'Total']

    @property
    def term(self):
        if self.year and self.month:
            return Period.valid_term[0]
        elif self.year:
            return Period.valid_term[1]
        elif not self.month:
            return Period.valid_term[2]
        else:
            raise Exception('Invalid combination of year: %s and month: %s' % (self.year, self.month))


class Statistic(models.Model):
    period = models.ForeignKey(Period, on_delete=models.PROTECT)
    content_type = models.ForeignKey(ContentType, null=True, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField(null=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    transferred_past = models.PositiveIntegerField('Transferred in Past', default=0)
    transferred_live = models.PositiveIntegerField('Transferred on Living Port', default=0)
    dt_collected = models.DateTimeField('Collected', null=True, blank=True)
    dt_created = models.DateTimeField('Created', auto_now_add=True)
    dt_updated = models.DateTimeField('Updated', auto_now=True)

    class Meta:
        verbose_name = 'Statistic'
        verbose_name_plural = verbose_name
        unique_together = ('period', 'content_type', 'object_id')

    def __str__(self):
        return '%s %s %s' % (self.content_object, self.transferred, self.period)

    @property
    def transferred(self):
        return self.transferred_past + self.transferred_live

    valid_cls = [NodeAccount, Node, Account]

    @property
    def object_type(self):
        if not self.content_type:
            return 'None'
        cls = self.content_type.model_class()
        if cls in Statistic.valid_cls:
            return cls.__name__
        else:
            raise Exception('%s: invalid class: %s, valid classes are: %s' % (self, cls, Statistic.valid_cls))

    @property
    def object_cls(self):
        if self.content_type:
            return self.content_type.model_class()

    @property
    def stat_type(self):
        p = self.period.term
        o = self.object_type
        return p + o

    depends = {
        'Monthly': {
            'Node': [NodeAccount, 'Monthly'],
            'Account': [NodeAccount, 'Monthly'],
            'None': [Node, 'Monthly']
        },
        'Yearly': {
            'NodeAccount': [NodeAccount, 'Monthly'],
            'Node': [Node, 'Monthly'],
            'Account': [Account, 'Monthly'],
            'None': [Node, 'Monthly']
        },
        'Total': {
            'NodeAccount': [NodeAccount, 'Yearly'],
            'Node': [Node, 'Yearly'],
            'Account': [Account, 'Yearly'],
            'None': [Node, 'Yearly']
        }
    }

    steps = [
        {
            'periods': [
                'Yearly',
                'Total'
            ],
            'cls': NodeAccount,
            'filter': {}
        },
        {
            'periods': [
                'Monthly',
                'Yearly',
                'Total'
            ],
            'cls': Node,
            'filter': {
                'is_active': True
            }
        },
        {
            'periods': [
                'Monthly',
                'Yearly',
                'Total'
            ],
            'cls': Account,
            'filter': {
                'is_active': True
            }
        },
        {
            'periods': [
                'Monthly',
                'Yearly',
                'Total'
            ],
            'cls': None,
            'filter': {}
        }
    ]

    @property
    def depend(self):
        obj = Statistic.depends.get(self.period.term)
        ret = obj.get(self.object_type) if obj else None
        if ret:
            return ret
        else:
            raise Exception('%s: failed to get depends: %s, %s' % (self, self.period.term, self.stat_type))

    @property
    def consolidate_filter(self):
        depend = self.depend

        lower_cls_name = depend[0].__name__.lower()
        kwargs = {
            'content_type__model': lower_cls_name
        }

        if self.content_type:
            if depend[0] == self.content_type.model_class():
                kwargs[lower_cls_name] = self.content_object
            else:
                kwargs['%s__%s' % (lower_cls_name, self.content_type.model)] = self.content_object

        if depend[1] == 'Monthly':
            kwargs['period__year'] = self.period.year
            if self.period.term == depend[1]:
                kwargs['period__month'] = self.period.month
            else:
                kwargs['period__month__isnull'] = False
        elif depend[1] == 'Yearly':
            if self.period.term == depend[1]:
                kwargs['period__year'] = self.period.year
            else:
                kwargs['period__year__isnull'] = False
            kwargs['period__month__isnull'] = True
        elif depend[1] == 'Total':
            kwargs['period__year__isnull'] = True
            kwargs['period__month__isnull'] = True

        if kwargs:
            return kwargs
        else:
            raise Exception('%s: failed to get consolidate filter: %s' % (self, depend))

    def consolidate(self):
        transferred_past = 0
        transferred_live = 0

        stats = self.__class__.objects.filter(**self.consolidate_filter)
        for obj in stats:
            transferred_past += obj.transferred_past
            transferred_live += obj.transferred_live
            if self.dt_collected is None:
                self.dt_collected = obj.dt_collected
            elif obj.dt_collected and obj.dt_collected > self.dt_collected:
                self.dt_collected = obj.dt_collected

        self.transferred_past = transferred_past
        self.transferred_live = transferred_live
        self.save()

    @classmethod
    @lock('statistic.collect', blocking=False)
    def collect(cls):
        # Collect the base statistic data depended by all other statistic
        for node in Node.objects.filter(is_active=True):
            ts = timezone.now()
            ss_stat = node.ssmanager.ping_ex() if node.ssmanager else None
            if ss_stat:
                # NodeAccount Monthly
                for na in node.accounts_ref.filter(is_active=True):
                    (period, created) = Period.objects.get_or_create(
                        year=ts.year,
                        month=ts.month)

                    (stat, created) = Statistic.objects.get_or_create(
                        period=period,
                        content_type=ContentType.objects.get_for_model(na),
                        object_id=na.pk)

                    transferred_live = ss_stat.get(stat.content_object.account.username, 0)
                    if transferred_live < stat.transferred_live:
                        # changing active/inactive status or restarting server clears the statistic
                        stat.transferred_past += stat.transferred_live
                    else:
                        pass

                    stat.transferred_live = transferred_live
                    stat.dt_collected = ts
                    stat.save()
            else:
                # do nothing if no stat data returned
                pass

    @classmethod
    @lock('statistic.statistic', blocking=False)
    def statistic(cls):
        cls.collect()

        ts = timezone.now()
        for step in Statistic.steps:
            kwargs = {}
            step_cls = step.get('cls')

            if step_cls:
                kwargs['content_type'] = ContentType.objects.get_for_model(step_cls)
                objs = step_cls.objects.filter(**step.get('filter'))
            else:
                kwargs['content_type'] = None
                kwargs['object_id'] = None
                objs = []

            for period in step.get('periods'):
                period_kwargs = {}

                if period == 'Monthly':
                    period_kwargs['year'] = ts.year
                    period_kwargs['month'] = ts.month
                elif period == 'Yearly':
                    period_kwargs['year'] = ts.year
                    period_kwargs['month'] = None
                elif period == 'Total':
                    period_kwargs['year'] = None
                    period_kwargs['month'] = None
                else:
                    raise Exception('%s: invalid period defined in step: %s\n%s' % (cls, period, step))

                kwargs['period'] = Period.objects.get_or_create(**period_kwargs)[0]

                if objs:
                    for obj in objs:
                        kwargs['object_id'] = obj.pk
                        (stat, created) = Statistic.objects.get_or_create(**kwargs)
                        stat.consolidate()
                else:
                    (stat, created) = Statistic.objects.get_or_create(**kwargs)
                    stat.consolidate()

    @classmethod
    @lock('statistic.collect', blocking=300) # wait for 5 minutes
    def reset(cls):
        # recreate all active ports
        nas = NodeAccount.objects.filter(is_active=True)

        for na in nas:
            na.on_delete()

        # use separate loops, let the recreation pause a moment,
        # to wait for the port updating take effect.
        for na in nas:
            na.on_update()
