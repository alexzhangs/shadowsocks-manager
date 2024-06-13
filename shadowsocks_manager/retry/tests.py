# -*- coding: utf-8 -*-

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals
from __future__ import absolute_import

from unittest import TestCase

from retry import retry


import logging
# Get a logger for this django app
logger = logging.getLogger(__name__.split('.')[-2])
# Set the logging level to make the output clean
logger.setLevel(logging.CRITICAL)


# Create your tests here.
class RetryTestCase(TestCase):
    def setUp(self):
        self.retryee = Retryee()

    def test_retry_positive(self):
        self.assertTrue(self.retryee.call(success_on_retry=0, retry_count=0))
        self.assertTrue(self.retryee.call(success_on_retry=1, retry_count=3))
        self.assertTrue(self.retryee.call(success_on_retry=2, retry_count=3))
        self.assertTrue(self.retryee.call(success_on_retry=3, retry_count=3))

    def test_retry_negative(self):

        self.assertFalse(self.retryee.call(success_on_retry=1, retry_count=0))
        self.assertFalse(self.retryee.call(success_on_retry=4, retry_count=3))

class Retryee:
    def call(self, success_on_retry, retry_count):
        """
        Set the decorator @retry(count=retry_count) on retryee().
        Call with: retryee(success_on_retry=success_on_retry).
        """
        # reset the global counter before calling retryee()
        self.RETRIED = 0

        @retry(count=retry_count, delay=0.1, logger=logger)
        def retryee(success_on_retry):
            """
            Return True if the retried times is equal to the success_on_retry.
            """
            result = self.RETRIED == success_on_retry
            self.RETRIED += 1
            return result

        return retryee(success_on_retry)
