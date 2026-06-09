"""
Django settings for shadowsocks_manager project.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.2/ref/settings/
"""

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals

import os
from decouple import Config, RepositoryEnv

from utils.version import get_version


def get_env_file(ssm_data_home):
    env_file = os.path.join(ssm_data_home, '.ssm-env')
    if not os.path.exists(env_file):
        # create the .ssm-env file if it does not exist
        with open(env_file, 'w') as f:
            f.write('')
    return env_file

# get the Django root directory
DJANGO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# get the project root directory
PROJECT_ROOT = os.path.dirname(DJANGO_ROOT)

# get SSM_DATA_HOME from environment, or use ~/.ssm-data as default
DATA_HOME = os.getenv('SSM_DATA_HOME') or os.path.expanduser('~/.ssm-data')
print('shadowsocks-manager [{}]: DATA_HOME: {}'.format(os.getpid(), DATA_HOME))

# create the DATA_HOME directory if it does not exist
if not os.path.exists(DATA_HOME):
    os.makedirs(DATA_HOME)

config = Config(RepositoryEnv(get_env_file(DATA_HOME)))

# get the full version
VERSION = get_version(full=True)
print('shadowsocks-manager [{}]: VERSION: {}'.format(os.getpid(), VERSION))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SSM_SECRET_KEY', default='ef24ff499c58a21711385e8a6b31a7680fb41765b8ca0cb451')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('SSM_DEBUG', default=True, cast=bool)
print('shadowsocks-manager [{}]: DEBUG: {}'.format(os.getpid(), DEBUG))

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# set ALLOWED_HOSTS
ALLOWED_SITES_DEFAULTS = config('SSM_ALLOWED_SITES_DEFAULTS', default='localhost,127.0.0.1')
ALLOWED_SITES_DEFAULTS = {item.lower() for item in ALLOWED_SITES_DEFAULTS.split(',') if item}

ALLOWED_SITES_DEFAULTS_PLUS = config('SSM_ALLOWED_SITES_DEFAULTS_PLUS', default='')
ALLOWED_SITES_DEFAULTS_PLUS = {item.lower() for item in ALLOWED_SITES_DEFAULTS_PLUS.split(',') if item}

ALLOWED_SITES_DYNAMIC_PUBLIC_IP = config('SSM_ALLOWED_SITES_DYNAMIC_PUBLIC_IP', default=False, cast=bool)
ALLOWED_SITES_NET_TIMEOUT = config('SSM_ALLOWED_SITES_NET_TIMEOUT', default=5, cast=int)
ALLOWED_SITES_CACHE_TIMEOUT = config('SSM_ALLOWED_SITES_CACHE_TIMEOUT', default=180, cast=int)

from allowedsites import CachedAllowedSites


# Django 5 enforces isinstance(ALLOWED_HOSTS, (list, tuple)) at settings-load
# time. CachedAllowedSites provides __contains__/__iter__ (which is all the
# host-matching logic in HttpRequest.validate_host() actually uses) but is not
# a list/tuple subclass, so Django 5 rejects it outright.
#
# Wrap it in a list subclass so the isinstance check passes while preserving
# dynamic host resolution via the wrapped object's __contains__.
class _DynamicAllowedHosts(list):
    def __init__(self, inner):
        super().__init__()
        self._inner = inner
    def __contains__(self, item):
        return item in self._inner
    def __iter__(self):
        return iter(self._inner)
    def __bool__(self):
        return True
    def __repr__(self):
        return f"_DynamicAllowedHosts({self._inner!r})"


ALLOWED_HOSTS = _DynamicAllowedHosts(CachedAllowedSites(
    defaults=ALLOWED_SITES_DEFAULTS.union(ALLOWED_SITES_DEFAULTS_PLUS),
    dynamic_public_ip=ALLOWED_SITES_DYNAMIC_PUBLIC_IP,
    net_timeout=ALLOWED_SITES_NET_TIMEOUT,
    cache_timeout=ALLOWED_SITES_CACHE_TIMEOUT,
))

# set the SITE_ID, make sure there's a fixture for the site
SITE_ID = 1


# Proxy-aware HTTPS detection
#
# Behind nginx (which terminates TLS and forwards to uwsgi as plain HTTP),
# request.is_secure() defaults to False and CSRF middleware on Django 4+
# refuses POSTs without matching CSRF_TRUSTED_ORIGINS. Tell Django to honor
# the X-Forwarded-Proto header set by the bundled nginx config so
# is_secure() correctly returns True for HTTPS-originated requests.
#
# Override with SSM_SECURE_PROXY_SSL_HEADER=disable on deployments that
# don't have a trusted reverse proxy in front (in which case Django should
# NOT trust the header — it can be forged by a direct client).
SECURE_PROXY_SSL_HEADER_RAW = config('SSM_SECURE_PROXY_SSL_HEADER',
                                     default='HTTP_X_FORWARDED_PROTO,https')
if SECURE_PROXY_SSL_HEADER_RAW.lower() in {'disable', 'none', ''}:
    SECURE_PROXY_SSL_HEADER = None
else:
    _hdr, _val = SECURE_PROXY_SSL_HEADER_RAW.split(',', 1)
    SECURE_PROXY_SSL_HEADER = (_hdr.strip(), _val.strip())


# CSRF trusted origins
#
# Django 4+ enforces a separate CSRF check against Origin/Referer for
# unsafe (POST/PUT/DELETE/PATCH) requests. The host must appear in
# CSRF_TRUSTED_ORIGINS with explicit scheme. ALLOWED_HOSTS no longer
# implies CSRF trust (it did in Django 3.x).
#
# Populate via SSM_CSRF_TRUSTED_ORIGINS as comma-separated scheme+host:
#   SSM_CSRF_TRUSTED_ORIGINS=https://admin.ss.example.com
CSRF_TRUSTED_ORIGINS_RAW = config('SSM_CSRF_TRUSTED_ORIGINS', default='')
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in CSRF_TRUSTED_ORIGINS_RAW.split(',') if o.strip()
]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django_celery_beat',
    'django_celery_results',
    'admin_lazy_load',
    'import_export',
    'rest_framework',
    'django_filters',
    'args_formatter',
    'dynamicmethod',
    'retry',
    'singleton',
    'shadowsocks',
    'statistic',
    'notification',
    'domain',
    'utils',
    'fixture',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# prefix package name to allow being called outside of django environment
ROOT_URLCONF = 'shadowsocks_manager.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# prefix package name to allow being called outside of django environment
WSGI_APPLICATION = 'shadowsocks_manager.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DB_ROOT = os.path.join(DATA_HOME, 'db')
if not os.path.exists(DB_ROOT):
    os.makedirs(DB_ROOT)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(DB_ROOT, 'db.sqlite3'),
        'TEST': {
            'NAME': os.path.join(DB_ROOT, 'db-test.sqlite3'),
        },
    }
}
if not os.path.exists(DATABASES['default']['NAME']):
    print('shadowsocks-manager [{}]: fresh database file: {}'.format(os.getpid(), DATABASES['default']['NAME']))


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = config('SSM_TIME_ZONE', default='UTC')

USE_I18N = True

# USE_L10N was removed in Django 5.0 (deprecated since 4.0; localized
# formatting is enabled implicitly by USE_I18N).

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = '/static/'

STATIC_ROOT = os.path.join(DATA_HOME, 'static')


# Django REST Framework
# http://www.django-rest-framework.org

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        #'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly',
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        #'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend'
    ]
}


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}


# Memcached

CACHES_BACKEND = config('SSM_CACHES_BACKEND', default='locmem.LocMemCache')

# Backward-compat: `memcached.MemcachedCache` (the python-memcached driver) was
# removed in Django 4.1. Deployments upgraded in place from Django 3.x still have
# `SSM_CACHES_BACKEND=memcached.MemcachedCache` persisted in their .ssm-env, which
# would raise InvalidCacheBackendError on Django 5 and stop the manager booting.
# Transparently map the dropped alias to the supported PyMemcacheCache driver so
# existing deployments survive the upgrade without manual reconfiguration.
if CACHES_BACKEND == 'memcached.MemcachedCache':
    import warnings
    warnings.warn(
        "SSM_CACHES_BACKEND=memcached.MemcachedCache was removed in Django 4.1; "
        "falling back to memcached.PyMemcacheCache. Set "
        "SSM_CACHES_BACKEND=memcached.PyMemcacheCache to silence this warning.",
        DeprecationWarning,
    )
    CACHES_BACKEND = 'memcached.PyMemcacheCache'

MEMCACHED_HOST = config('SSM_MEMCACHED_HOST', default='localhost')
MEMCACHED_PORT = config('SSM_MEMCACHED_PORT', default='11211')

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.{}'.format(CACHES_BACKEND),
    }
}
# memcached.MemcachedCache was removed in Django 4.1 (alias for the dropped
# python-memcached driver). On Django 5 the supported drivers are
# PyMemcacheCache (recommended, pure-python, uses pymemcache pkg) and
# PyLibMCCache. Match any memcached.* backend so deployments setting
# SSM_CACHES_BACKEND=memcached.PyMemcacheCache get the LOCATION wired.
if CACHES_BACKEND.startswith('memcached.'):
    CACHES['default']['LOCATION'] = '{}:{}'.format(MEMCACHED_HOST, MEMCACHED_PORT)


# Celery

RABBITMQ_HOST = config('SSM_RABBITMQ_HOST', default='localhost')
RABBITMQ_PORT = config('SSM_RABBITMQ_PORT', default='5672')

CELERY_RESULT_BACKEND = 'django-db'
CELERY_CACHE_BACKEND = 'django-cache'
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_BROKER_URL = 'amqp://guest:guest@{}:{}//'.format(RABBITMQ_HOST, RABBITMQ_PORT)
