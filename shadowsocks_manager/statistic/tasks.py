# Create your tasks here

# py2.7 and py3 compatibility imports
from __future__ import absolute_import, unicode_literals

from celery import shared_task

from .models import Statistic


@shared_task
def statistic():
    return Statistic.statistic()

@shared_task
def reset():
    return Statistic.reset()
