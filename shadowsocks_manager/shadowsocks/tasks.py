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

# IMPORTANT: this task must NOT use acks_late / reject_on_worker_lost.
# change_ips_softly blocks the worker for ~6 min per node (DNS TTL + Config
# wait). With late acks the message stays unacked for the whole run; the
# blocking sleep also lapses the AMQP heartbeat (see CELERY_BROKER_HEARTBEAT
# in settings), so the broker drops the connection and REDELIVERS the still-
# unacked message — turning one scheduled fire into an endless ~6-min rotation
# loop (the 2026 IP-rotation incident; observed redelivered=N/N in the queue).
# Early ack (the default) means the message is acked at delivery: a worker
# dying mid-run loses only that single run — recovered by the next schedule and
# the is_active finally-guard in change_ips_softly — instead of looping forever.
@shared_task(acks_late=False)
def node_change_ips_softly():
    return Node.change_ips_softly()
