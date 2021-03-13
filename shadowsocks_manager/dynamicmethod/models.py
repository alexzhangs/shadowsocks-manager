# -*- coding: utf-8 -*-

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals
import six

import types, importlib
import logging
from django.db import models


logger = logging.getLogger('django')


# Create your models here.

class DynamicMethodModel(object):

    """
    Usage:
      Inherit this class and set `dynamic_methods` in the subclass.
      Methods will be created with `dynamic_methods.template` and be available
      under the name of `dynamic_methods.method`.keys().
      Each '%s' within `dynamic_methods.template` will be replaced with the value
      of `variables`.
      Set `property` True if want a @property decorator on the dynamic method.

    Example:

    class Person(models.Model, DynamicMethodModel):
        dynamic_methods = [{
            "template": '''
                def pet(self):
                    return '%s %s %s.'
                ''',
            "method": {
                "dog": {
                    "variables": ["one", "black", "dog"],
                    'property': False
                },
                "cat": {
                    "variables": ["two", "white", "cats"],
                    'property': False
                },
                ...
            }
        }]

    obj = Person()
    obj.dog()   # 'one black dog.'
    obj.cat()   # 'two white cats.'
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

                self.create_method(
                    data=template % tuple(variables),
                    name=key,
                    decorator={'property': prop}
                )

    def create_method(self, data, name, decorator=None):
        if isinstance(data, six.text_type):
            try:
                code = compile(data, '<stdin>', 'exec')
            except SyntaxError as e:
                logger.error(e)
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
