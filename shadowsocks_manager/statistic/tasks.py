# Create your tasks here
from __future__ import absolute_import, unicode_literals
from celery import shared_task

from .models import Statistic


@shared_task
def statistics():
    return Statistic.statistics()

@shared_task
def reset():
    return Statistic.reset()
