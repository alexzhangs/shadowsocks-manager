"""
Django settings for shadowsocks_manager project.

Generated by 'django-admin startproject' using Django 1.11.20.

For more information on this file, see
https://docs.djangoproject.com/en/1.11/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.11/ref/settings/
"""

# py2.7 and py3 compatibility imports
from __future__ import unicode_literals

from decouple import Config, RepositoryEnv

import os


def get_env_file(ssm_data_home):
    env_file = os.path.join(ssm_data_home, '.ssm-env')
    if not os.path.exists(env_file):
        # create the .ssm-env file if it does not exist
        with open(env_file, 'w') as f:
            f.write('')
    return env_file


# get SSM_DATA_HOME from environment, or use Django root directory as default
DATA_HOME = os.getenv('SSM_DATA_HOME') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# create the DATA_HOME directory if it does not exist
if not os.path.exists(DATA_HOME):
    os.makedirs(DATA_HOME)

config = Config(RepositoryEnv(get_env_file(DATA_HOME)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.11/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SSM_SECRET_KEY', default='ef24ff499c58a21711385e8a6b31a7680fb41765b8ca0cb451')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('SSM_DEBUG', default=True, cast=bool)

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
ALLOWED_HOSTS = CachedAllowedSites(
    defaults=ALLOWED_SITES_DEFAULTS.union(ALLOWED_SITES_DEFAULTS_PLUS),
    dynamic_public_ip=ALLOWED_SITES_DYNAMIC_PUBLIC_IP,
    net_timeout=ALLOWED_SITES_NET_TIMEOUT,
    cache_timeout=ALLOWED_SITES_CACHE_TIMEOUT,
)

# set the SITE_ID, make sure there's a fixture for the site
SITE_ID = 1


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
    'import_export',
    'rest_framework',
    'django_filters',
    'shadowsocks',
    'statistic',
    'notification',
    'domain',
    'utils',
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
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases

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


# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/1.11/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = config('SSM_TIME_ZONE', default='UTC')

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/

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
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}


# Memcached

MEMCACHED_HOST = config('SSM_MEMCACHED_HOST', default='localhost')
MEMCACHED_PORT = config('SSM_MEMCACHED_PORT', default='11211')

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '{}:{}'.format(MEMCACHED_HOST, MEMCACHED_PORT),
    }
}


# Celery

RABBITMQ_HOST = config('SSM_RABBITMQ_HOST', default='localhost')
RABBITMQ_PORT = config('SSM_RABBITMQ_PORT', default='5672')

CELERY_RESULT_BACKEND = 'django-db'
CELERY_CACHE_BACKEND = 'django-cache'
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_BROKER_URL = 'amqp://guest:guest@{}:{}//'.format(RABBITMQ_HOST, RABBITMQ_PORT)
