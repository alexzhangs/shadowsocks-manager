from django_lock import lock

'''
See document: https://github.com/Xavier-Lam/django-cache-lock
And check out the help: help(django_lock.lock)

This patchs django.core.cache.cache a lock() method.
'''

lock.patch_cache()
