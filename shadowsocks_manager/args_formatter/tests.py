# -*- coding: utf-8 -*-

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals
from __future__ import absolute_import

from unittest import TestCase

from . import Formatter

# Create your tests here.
class FormatterTestCase(TestCase):
    def test(self):
        self.assertEqual(Formatter().to_string(), '')
        self.assertEqual(Formatter(None).to_string(), 'None')
        self.assertEqual(Formatter("").to_string(), "''")
        self.assertEqual(Formatter('foo', 1).to_string(), "'foo', 1")
        self.assertEqual(Formatter(["foo", 1]).to_string(), "['foo', 1]")
        self.assertEqual(Formatter({"foo": 1}).to_string(), "{'foo': 1}")
        self.assertEqual(Formatter(("foo", 1)).to_string(), "('foo', 1)")
        self.assertEqual(Formatter(x='bar', y=2).to_string(), "x='bar', y=2")
        self.assertEqual(Formatter(x=['bar', 2]).to_string(), "x=['bar', 2]")
        self.assertEqual(Formatter(x={'bar': 2}).to_string(), "x={'bar': 2}")
        self.assertEqual(Formatter(x=('bar', 2)).to_string(), "x=('bar', 2)")
        self.assertEqual(Formatter('foo', 1, x='bar', y=2).to_string(), "'foo', 1, x='bar', y=2")
