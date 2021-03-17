# -*- coding: utf-8 -*-

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals
from __future__ import absolute_import
from builtins import str

from unittest import TestCase

from . import Formatter

# Create your tests here.
class FormatterTestCase(TestCase):
    def test(self):
        # no args and kwargs
        self.assertEqual(Formatter().to_string(), '')
        # one arg as None
        self.assertEqual(Formatter(None).to_string(), 'None')
        # one arg as empty string
        self.assertEqual(Formatter('').to_string(), repr(''))
        # two simple args
        self.assertEqual(Formatter('foo', 1).to_string(), '{}, 1'.format(repr('foo')))
        # one arg as list
        self.assertEqual(Formatter(['foo', 1]).to_string(), '[{}, 1]'.format(repr('foo')))
        # one arg as dict
        self.assertEqual(Formatter({'foo': 1}).to_string(), repr({'foo': 1}))
        # on arg as tuple
        self.assertEqual(Formatter(('foo', 1)).to_string(), repr(('foo', 1)))
        # two simple kwargs, take care of the order, so works with both py2 and py3
        self.assertEqual(Formatter(y=2, x='bar').to_string(), 'y=2, x={}'.format(repr('bar')))
        # one kwarg as list
        self.assertEqual(Formatter(x=['bar', 2]).to_string(), 'x={}'.format(repr(['bar', 2])))
        # one kwarg as dict
        self.assertEqual(Formatter(x={'bar': 2}).to_string(), 'x={}'.format(repr({'bar': 2})))
        # one kwarg as tuple
        self.assertEqual(Formatter(x=('bar', 2)).to_string(), 'x={}'.format(repr(('bar', 2))))
        # two simple args and two simple kwargs, take care of the order, so works with both py2 and py3
        self.assertEqual(
            Formatter('foo', 1, y=2, x='bar').to_string(),
            '{}, 1, y=2, x={}'.format(repr('foo'), repr('bar')))
        # __str__()
        self.assertEqual(str(Formatter(None)), 'None')
