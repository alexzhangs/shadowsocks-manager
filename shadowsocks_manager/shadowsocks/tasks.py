# Create your tasks here

# py2.7 and py3 compatibility imports
from __future__ import absolute_import, unicode_literals

from celery import shared_task

from .models import Node, NodeAccount


@shared_task
def port_heartbeat():
    return NodeAccount.heartbeat()

@shared_task
def node_change_ips():
    return Node.change_ips()

# acks_late + reject_on_worker_lost: change_ips_softly runs for ~10 min per
# node and was the task in flight when a celery worker hung in D-state during
# the IP-rotation incident. With late acks the broker only drops the message
# after the task finishes, and reject_on_worker_lost requeues it (instead of
# silently discarding) if the worker is killed (e.g. `pkill -9 celery`) mid-run.
@shared_task(acks_late=True, reject_on_worker_lost=True)
def node_change_ips_softly():
    return Node.change_ips_softly()
