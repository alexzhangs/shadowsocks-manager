# py2.7 and py3 compatibility imports
from __future__ import unicode_literals
from builtins import range
from builtins import object

import time
from functools import wraps

from args_formatter import Formatter


class Retry(object):

    def __init__(self, count, delay, logger, level, *args, **kwargs):
        super(Retry, self).__init__(*args, **kwargs)
        self.count = count
        self.delay = delay
        self.logger = getattr(logger, level) if logger else None

    def __call__(self, func):

        @wraps(func)
        def _retry(*args, **kwargs):
            # run at lease once and don't count as retry
            for attempts in range(self.count + 1):
                ret = func(*args, **kwargs)

                if ret:
                    return ret
                elif attempts < self.count:
                    self.log_retry(func, attempts + 1)
                    self.log_params(*args, **kwargs)
                    time.sleep(self.delay)
                else:
                    self.log_failure(func)
                    self.log_params(*args, **kwargs)
        return _retry

    def log_retry(self, func, attempts):
        if self.logger:
            msg = '{func}: Retrying {attempts} of {count} in {delay} second(s)...'.format(
                func=func, attempts=attempts, count=self.count, delay=self.delay)
            self.logger(msg)

    def log_failure(self, func):
        if self.logger:
            msg = '{func}: Failed.'.format(func=func)
            self.logger(msg)

    def log_params(self, *args, **kwargs):
        if self.logger and (args or kwargs):
            msg = 'params: {}'.format(Formatter(*args, **kwargs).to_string())
            self.logger(msg)


def retry(count=5, delay=0, logger=None, level='info'):
    """
    :param count:  max retry times, count=0 means no retry.
    :param delay:  delay <N> seconds between retries.
    :param logger: log retries and final failure if a logger is given.
    :param level:  log the message to this level.

        from retry import retry

        @retry(count=3, delay=1, logger=mylogger, level='warning')
        def foo():
          return None
    """

    return Retry(
        count=count, delay=delay, logger=logger, level=level)
