# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import subprocess
from subprocess import PIPE
from django.db import models
from django.template import engines, TemplateSyntaxError
from django.template.loader import render_to_string

from singleton.models import SingletonModel


logger = logging.getLogger('django')


# Create your models here.

class Template(models.Model):
    type = models.CharField(max_length=32, choices=[('account_created', 'Account Created')])
    content = models.TextField()
    is_active = models.BooleanField(default=False)
    dt_created = models.DateTimeField('Created', auto_now_add=True)
    dt_updated = models.DateTimeField('Updated', auto_now=True)

    class Meta:
        verbose_name = 'Notification Template'
        unique_together = ('type', 'is_active')

    @property
    def template(self):
        return engines['django'].from_string(self.content)

    def __unicode__(self):
        return self.type

    def render(self, kwargs):
        if self.template:
            return self.template.render(kwargs)
        else:
            raise RuntimeError("The template '%s' is not correctly configured." % self)


class Notify(models.Model):

    @classmethod
    def sendmail(cls, message, sender, email):
        command = ["sendmail",
                       "-F", sender,
                       "-f", email,
                       "-t"]

        proc = subprocess.Popen(command, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        (stdout, stderr) = proc.communicate(message)

        rc = proc.wait()
        if rc != 0:
            logger.error('sendmail: return code: %s' % rc)
            logger.error(stderr)
            return False
        else:
            return True
