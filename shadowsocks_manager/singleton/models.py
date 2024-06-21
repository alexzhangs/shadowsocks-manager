# -*- coding: utf-8 -*-

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals

import logging
from django.db import models
from django.core.cache import cache


logger = logging.getLogger(__name__)


class CustomManager(models.Manager):
    def update(self, *args, **kwargs):
        super(CustomManager, self).update(*args, **kwargs)
        self.model.clear_cache()


class SingletonModel(models.Model):
    objects = CustomManager()

    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        pass

    def set_cache(self):
        cache.set(self.__class__.get_cache_key(), self)

    def save(self, *args, **kwargs):
        self.pk = 1
        super(SingletonModel, self).save(*args, **kwargs)

        self.set_cache()

    @classmethod
    def clear_cache(cls):
        cache.delete(cls.get_cache_key())

    @classmethod
    def get_cache_key(cls):
        return cls.__module__

    @classmethod
    def load(cls):
        obj = cache.get(cls.get_cache_key())
        if obj is None:
            logger.debug("No cached Singleton object: %s, trying to fetch it beyond cache." % cls.__name__)
            obj, created = cls.objects.get_or_create(pk=1)
            if not created:
                obj.set_cache()
                
        return obj
