# -*- coding: utf-8 -*-

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals
from __future__ import absolute_import

import json
from abc import abstractmethod
from django.test import TestCase

from notification import models, serializers


import logging
# disable logging for the test module to make the output clean
logging.disable(logging.CRITICAL)


class BaseTestCase(TestCase):
    """
    A base test case for current app.
    This class is inherited from Django TestCase class, and provides the following features:

    Set a list of default fixtures for all test cases in this app.
    * fixtures = []

    Set a list of test case class names, if the up() and down() class methods are defined in
    the sub-class, all of them can be called at once by calling the allup() and alldown() class 
    methods in this class.
    * testcases = []
    """

    fixtures = []
    testcases = []

    class meta:
        abstract = True

    @classmethod
    @abstractmethod
    def up(cls):
        """
        Set up the test environment.
        """
        pass

    @classmethod
    @abstractmethod
    def down(cls):
        """
        Tear down the test environment.
        """
        pass

    @classmethod
    def allup(cls):
        """
        Call the up() class method (if exists) in each class defined in the testcases list.
        """
        for testcase in [globals().get(name) for name in cls.testcases]:
            method = getattr(testcase or {}, 'up', None)
            if method: method()

    @classmethod
    def alldown(cls):
        """
        Call the down() class method (if exists) in each class defined in the testcases list.
        """
        for testcase in [globals().get(name) for name in cls.testcases]:
            method = getattr(testcase or {}, 'down', None)
            if method: method()


class AppTestCase(BaseTestCase):
    fixtures = ['template.json']
    testcases = []


class NotificationTestCase(AppTestCase):
    def test_template_template(self):
        for obj in models.Template.objects.all():
            self.assertTrue(obj.template)

    def test_template_account_created(self):
        pass  # todo

    def test_template_serializer(self):
        obj = serializers.TemplateSerializer()
        json.loads(json.dumps(obj.to_representation(models.Template.objects.first())))

    def test_notify_sendmail(self):
        message='Subject: shadowsocks test email\r\nTo: nobody@localhost\r\ndelete me.'
        self.assertTrue(models.Notify.sendmail(message, 'No Reply', 'noreply@localost'))
