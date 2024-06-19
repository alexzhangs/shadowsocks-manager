# py2.7 and py3 compatibility imports
from __future__ import unicode_literals
from builtins import object


class Formatter(object):
    """
    Return the input-syntax string presentation of args and kwargs list, delimited by comma `, `.
    The value of the args and kwargs are formatted as the canonical string presentation.
    The key order of the kwargs is not guaranteed in Python 3.6 and earlier.

    Usage:
        >>> f = Formatter(*args, **kwargs)
        >>> print(f)

    Example:
        >>> print(Formatter('foo', 1, x='bar', y=2))
        'foo', 1, x='bar', y=2

    Use Case:
        # log the input arguments of methods.
        def foo(*args, **kwargs):
            message = Formatter(*args, **kwargs).to_string())
            logger.debug('foo: {}'.format(message))
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize the Formatter to have two members: args, kwargs
        """
        self.args = args
        self.kwargs = kwargs

    def __str__(self):
        return self.to_string()

    def args_to_string(self):
        """
        Return the canonical string presentation of args list, delimited by comma `, `.
        """
        return ', '.join(repr(arg) for arg in self.args)

    def kwargs_to_string(self):
        """
        Return the input-syntax string presentation of kwargs list, delimited by comma `, `.
        The value of the kwargs are formatted as the canonical string presentation.
        """
        return ', '.join('{}={}'.format(k, repr(v)) for k, v in self.kwargs.items())

    def to_string(self):
        """
        Return the input-syntax string presentation of args and kwargs list, delimited by comma `, `.
        The value of the args and kwargs are formatted as the canonical string presentation.
        Be noted to the differences:
            * An empty string `` is returned if no args and kwargs found.
            * The input empty string `` is returned as the literal "``" with the additional quoting.
            * The input NoneType None is returned as the literal `None` without additional quoting.

        Example:
            >>> Formatter('foo', 1, x='bar', y=2).to_string()
            "'foo', 1, x='bar', y=2"
        """

        items = [self.args_to_string(), self.kwargs_to_string()]
        return ', '.join(item for item in items if item)
