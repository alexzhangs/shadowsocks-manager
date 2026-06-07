# -*- coding: utf-8 -*-

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals

from django.test import TestCase

from dynamicmethod.models import DynamicMethodModel


import logging
# Get a logger for this django app
logger = logging.getLogger(__name__.split('.')[-2])
# Set the logging level to make the output clean
logger.setLevel(logging.CRITICAL)


class PetStore(DynamicMethodModel):
    dynamic_methods = [
        {
            "template": '''
                def pets(self):
                    return '%s %s %s'
            ''',
            "method": {
                "dog": {
                    "variables": ["one", "black", "dog"],
                    'property': True
                },
                "cat": {
                    "variables": ["two", "white", "cats"],
                    'property': True
                },
            }
        },
        {
            "template": '''
                def pet_pets(self):
                    return '%s'
                ''',
            "method": {
                "pet_dog": {
                    "variables": ["woof"],
                    'property': False
                },
                "pet_cat": {
                    "variables": ["meow"],
                    'property': False
                },
            }
        }
    ]


class DynamicMethodModelTestCase(TestCase):

    def test_dynamicmethodmodel_positive_property_method(self):
        obj = PetStore()
        self.assertEqual(obj.dog, 'one black dog')
        self.assertEqual(obj.cat, 'two white cats')

    def test_dynamicmethodmodel_positive_method(self):
        obj = PetStore()
        self.assertEqual(obj.pet_dog(), 'woof')
        self.assertEqual(obj.pet_cat(), 'meow')

    def test_dynamicmethodmodel_negative(self):
        PetStore.dynamic_methods[1]['method']['pet_duck'] = {'variables': ['quack', 'quack']}
        obj = PetStore()
        self.assertFalse(hasattr(obj, 'pet_duck'))
        self.assertEqual(obj.pet_dog(), 'woof')
        self.assertEqual(obj.pet_cat(), 'meow')

    def test_create_method_syntax_error(self):
        obj = PetStore()
        result = obj.create_method(data='def bad(self: return', name='bad_method')
        self.assertIsNone(result)

    def test_create_method_non_string_non_code(self):
        obj = PetStore()
        result = obj.create_method(data=42, name='bad_method')
        self.assertIsNone(result)

    def test_create_method_precompiled_code(self):
        import textwrap
        import types
        code = compile(textwrap.dedent('def pet_fish(self): return "blub"').strip(), '<stdin>', 'exec')
        obj = PetStore()
        obj.create_method(data=code, name='pet_fish')
        self.assertEqual(obj.pet_fish(), 'blub')
