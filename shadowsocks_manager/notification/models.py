# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging, subprocess
from django.db import models
from django.template import engines, TemplateSyntaxError
from django.template.loader import render_to_string

from singleton.models import SingletonModel


logger = logging.getLogger('django')


# Create your models here.

class Config(SingletonModel):
    sender_name = models.CharField(max_length=32, default='VPN Service', help_text='Appears in the account notification Email.')
    sender_email = models.CharField(max_length=64, null=True, blank=True, help_text='Appears in the account notification Email, example: admin@shadowsocks.yourdomain.com.')
    dt_created = models.DateTimeField('Created', auto_now_add=True)
    dt_updated = models.DateTimeField('Updated', auto_now=True)

    class Meta:
        verbose_name = 'Notification Config'


class Template(models.Model):
    type = models.CharField(max_length=32, choices=[('account_created', 'Account Created')])
    content = models.TextField()
    is_active = models.BooleanField(default=False)
    dt_created = models.DateTimeField('Created', auto_now_add=True)
    dt_updated = models.DateTimeField('Updated', auto_now=True)

    class Meta:
        verbose_name = 'Notification Template'
        unique_together = ('type', 'is_active')

    def __init__(self, *args, **kwargs):
        super(Template, self).__init__(*args, **kwargs)

        self.template = None
        try:
            self.template = engines['django'].from_string(self.content)
        except TemplateSyntaxError as e:
            logger.error(e)

    def __unicode__(self):
        return self.type

    def render(self, kwargs):
        if self.template:
            return self.template.render(kwargs)
        else:
            logger.error("The template '%s' is not correctly configured." % self)


class Notify(models.Model):

    @classmethod
    def sendmail(cls, message):
        config = Config.load()
        command = ["sendmail",
                       "-F", config.sender_name,
                       "-f", config.sender_email,
                       "-t"]
        p = subprocess.Popen(command, stdin=subprocess.PIPE)
        p.communicate(message)
