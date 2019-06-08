# Create your tasks here
from __future__ import absolute_import, unicode_literals
from celery import shared_task

from .models import NodeAccount


@shared_task
def port_heartbeat():
    return NodeAccount.heartbeat()
