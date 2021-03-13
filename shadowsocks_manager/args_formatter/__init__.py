# py2.7 and py3 compatibility imports
from __future__ import unicode_literals
from functools import reduce


class Formatter(object):
    """
    Formatter('foo', 'bar', x=1, y=2).to_string()
    'foo, bar, y=2, x=1'
    """

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def args_to_string(self):
        if self.args:
            formatter = ['{}' for count in range(len(self.args))]
            return ', '.join(formatter).format(*self.args)

    def kwargs_to_string(self):
        if self.kwargs:
            formatter = ['{}={}' for count in range(len(self.kwargs))]
            return ', '.join(formatter).format(
                *reduce((lambda x, y: x + y), [list(item) for item in self.kwargs.items()]))

    def to_string(self):
        items = [self.args_to_string(), self.kwargs_to_string()]
        items = [item for item in items if item is not None]
        return ', '.join(items)
