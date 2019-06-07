# Create your tasks here
from __future__ import absolute_import, unicode_literals
from celery import shared_task

from .models import Statistics


@shared_task
def statistics():
    return Statistics.statistics()

@shared_task
def reset():
    return Statistics.reset()
