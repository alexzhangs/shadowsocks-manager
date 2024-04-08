# py2.7 and py3 compatibility imports
from __future__ import absolute_import, unicode_literals
from __future__ import print_function

import os
import sys
from celery import Celery

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shadowsocks_manager.shadowsocks_manager.settings')

app = Celery('shadowsocks_manager')

django_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# add the django root to the python path to allow django commands to be run from any directory
if django_root not in sys.path:
    sys.path.insert(0, django_root)

# change dir to the django root to allow the dir-sensitive commands(such as loaddata) to be run from any directory
os.chdir(django_root)

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

app.conf.broker_connection_retry_on_startup = True

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
