# -*- coding: utf-8 -*-

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals
from builtins import range
from builtins import object

import time
from functools import wraps
import logging

from args_formatter import Formatter


class Retry(object):

    def __init__(self, count, delay, logger, *args, **kwargs):
        super(Retry, self).__init__(*args, **kwargs)
        self.count = count
        self.delay = delay
        if logger:
            assert isinstance(logger, logging.Logger)
        self.logger = logger or logging.getLogger(__name__)

    def __call__(self, func):

        @wraps(func)
        def _retry(*args, **kwargs):
            # run at lease once and don't count as retry
            for attempts in range(self.count + 1):
                ret = func(*args, **kwargs)

                if ret:
                    self.logger.debug('{func}: Succeeded.'.format(func=func))
                    return ret
                elif attempts < self.count:
                    msg = '{func}: Retrying {attempts} of {count} in {delay} second(s)...'.format(
                        func=func, attempts=attempts, count=self.count, delay=self.delay)
                    self.logger.warning(msg)
                    time.sleep(self.delay)
                else:
                    self.logger.error('{func}: Failed.'.format(func=func))
                    self.logger.debug('params: {}'.format(Formatter(*args, **kwargs).to_string()))

        return _retry


def retry(count=5, delay=0, logger=None):
    """
    A decorator to enable automatically retry on the failure call of a function or method.

    The failure is evaluated by the return value of the function as it is falscy: `bool(RETURN_VALUE) == False`.
    >>> if not foo():  # retry is involved

    Option:
        * count:  max retry times, count=0 means no retry.
        * delay:  delay <N> seconds between retries.
        * logger: log retries and final failure if a logger is given.

    Example:
        from retry import retry

        @retry(count=3, delay=1, logger=mylogger)
        def foo():
          return None
    """

    return Retry(count=count, delay=delay, logger=logger)
