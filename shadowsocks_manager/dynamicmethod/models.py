# -*- coding: utf-8 -*-

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals
import six

import types
import textwrap
import logging


logger = logging.getLogger(__name__)


# Create your models here.

class DynamicMethodModel(object):

    """
    Usage:
      Inherit this class and set `dynamic_methods` in the subclass.
      Methods will be created with `dynamic_methods.template` and be available
      under the name of `dynamic_methods.method`.keys() at class level.
      Each '%s' within `dynamic_methods.template` will be replaced with the value
      of `variables`.
      Set `property` True if want a @property decorator on the dynamic method.

    Example:

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

    obj = PetStore()
    obj.dog         # 'one black dog'
    obj.cat         # 'two white cats'
    obj.pet_dog()   # 'woof'
    obj.pet_cat()   # 'meow'
    """

    dynamic_methods = []

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        super(DynamicMethodModel, self).__init__(*args, **kwargs)

        for dm in self.__class__.dynamic_methods:
            template = dm['template']
            method = dm['method']

            for key in list(method.keys()):
                m = method[key]
                variables = m.get('variables', None)
                prop = m.get('property', None)

                try:
                    data = template % tuple(variables)
                except TypeError as e:
                    logger.error('{}: {}: {}'.format(key, type(e).__name__, e))
                    continue

                self.create_method(
                    data=data,
                    name=key,
                    decorator={'property': prop}
                )

    def create_method(self, data, name, decorator=None):
        if isinstance(data, six.text_type):
            data = textwrap.dedent(data).strip()
            try:
                code = compile(data, '<stdin>', 'exec')
            except SyntaxError as e:
                logger.error('{}: {}: {}'.format(name, type(e).__name__, e))
                return None
        else:
            code = data

        if isinstance(code, types.CodeType):
            func = types.FunctionType(code.co_consts[0], globals())
        else:
            logger.error('Unable to generate FunctionType with the input data: %s' % data)
            return None

        if decorator and decorator.get('property', None):
            func = property(func)

        setattr(self.__class__, name, func)
