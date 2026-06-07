# -*- coding: utf-8 -*-

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals
from __future__ import absolute_import

import json
from abc import abstractmethod
from django.test import TestCase
from unittest.mock import patch, MagicMock, PropertyMock

from notification import models, serializers


import logging
# Get a logger for this django app
logger = logging.getLogger(__name__.split('.')[-2])
# Set the logging level to make the output clean
logger.setLevel(logging.ERROR)


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

    def test_template_str(self):
        obj = models.Template.objects.first()
        self.assertEqual(str(obj), obj.type)

    def test_template_render(self):
        obj = models.Template.objects.first()
        result = obj.render({})
        self.assertIsInstance(result, str)

    def test_template_render_falsy_template(self):
        obj = models.Template.objects.first()
        with patch.object(models.Template, 'template', new_callable=PropertyMock) as mock_tmpl:
            mock_tmpl.return_value = None
            with self.assertRaises(RuntimeError):
                obj.render({})

    def test_notify_sendmail_failure(self):
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = (b'', b'error')
        mock_proc.wait.return_value = 1
        with patch('notification.models.subprocess.Popen', return_value=mock_proc):
            result = models.Notify.sendmail('Subject: test\r\n', 'No Reply', 'noreply@localhost')
        self.assertFalse(result)
