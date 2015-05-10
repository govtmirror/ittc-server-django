"""
Django settings for ittc project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Imports
from __future__ import absolute_import
import os
from kombu import Queue
from celery.schedules import crontab

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '9u$pbamv*a1s09(5grvnko2)n)isa50=uui@lm3syhp6)jyrhg'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

# Note that Django automatically includes the "templates" dir in all the
# INSTALLED_APPS, se there is no need to add maps/templates or admin/templates
TEMPLATE_DIRS = (
    os.path.join(BASE_DIR, "ittc/templates"),
)

ALLOWED_HOSTS = []


# Application definition

ITTC_APPS = (
    'ittc.capabilities',
    'ittc.cache',
    'ittc.proxy',
    'ittc.source',
)

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Theme
    #"pinax_theme_bootstrap_account",
    "pinax_theme_bootstrap",
    'django_forms_bootstrap',

    'corsheaders',
    #'leaflet',
    'jquery',

) + ITTC_APPS

MIDDLEWARE_CLASSES = (
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'ittc.urls'

WSGI_APPLICATION = 'ittc.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/
#STATIC_ROOT = os.path.join(BASE_DIR, "static_root")
STATIC_ROOT = '/var/www/ittc/static/'
STATIC_URL = '/static/'
#STATICFILES_DIRS = [
#    os.path.join(BASE_DIR, "static"),
#]
#STATICFILES_FINDERS = (
#    'django.contrib.staticfiles.finders.FileSystemFinder',
#    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#)

#LEAFLET_CONFIG = {
#    'TILES': [
#        # Find tiles at:
#        # http://leaflet-extras.github.io/leaflet-providers/preview/
#
#        ('OpenStreetMap',
#         'http://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png',
#         '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>, Tiles courtesy of <a href="http://hot.openstreetmap.org/" target="_blank">Humanitarian OpenStreetMap Team</a>'),
#    ]
#}

CACHES = {
    'default': {
        'BACKEND': 'memcachepool.cache.UMemcacheCache',
        'LOCATION': '127.0.0.1:11211',
        'OPTIONS': {
            'MAX_POOL_SIZE': 40,
            'BLACKLIST_TIME': 60,
            'SOCKET_TIMEOUT': 60,
            'MAX_ITEM_SIZE': 1000*1000*1000
        }
    },
    'tiles': {
        'BACKEND': 'memcachepool.cache.UMemcacheCache',
        'LOCATION': '127.0.0.1:11212',
        'OPTIONS': {
            'MAX_POOL_SIZE': 40,
            'BLACKLIST_TIME': 60,
            'SOCKET_TIMEOUT': 5,
            'MAX_ITEM_SIZE': 1000*1000*1000
        }
    },
    'celery_results': {
        'BACKEND': 'memcachepool.cache.UMemcacheCache',
        'LOCATION': '127.0.0.1:11213',
        'OPTIONS': {
            'MAX_POOL_SIZE': 40,
            'BLACKLIST_TIME': 60,
            'SOCKET_TIMEOUT': 5,
            'MAX_ITEM_SIZE': 1000*1000*1000
        }
    }
}

###Settings ITTC Capabilities
TILE_ACCELERATOR = {
    'name': 'Tile Accelerator',
    'cache': {
        'memory': {
            'enabled': True,
            'type':'memory',
            'description': 'Main in-memory cache for tiles.',
            'target':'tiles',
            'minZoom': 0,
            'maxZoom': 18,
            'expiration': 'origin'
        }
    },
    'heuristic': {
        'down': {
            'enabled': False,
            'description':'Indirectly requests the 4 tiles beneath the requested tile.',
            'depth': 1,
            'minZoom': 0,
            'maxZoom': 18
        },
        'up': {
            'enabled': False,
            'description': 'Indirectly requests all tiles above the requested tile.  All tiles within a zoom level of "depth" are indirectly requested.',
            'depth': 1
        },
        'nearby': {
            'enabled': True,
            'description': 'Indirectly requests all neighboring tiles within a given radius.',
            'radius': 3
        }
    }
}

SITEURL = "http://localhost:8000/"

CORS_ORIGIN_ALLOW_ALL = True

PROXY_ALLOWED_HOSTS = ( 'tile.openstreetmap.org', 'tile.openstreetmap.fr', 'tiles.virtualearth.net', 'tiles.mapbox.com', 'hiu-maps.net' )

PROXY_URL = '/proxy/?url='

# Celery Settings
CELERY_RESULT_BACKEND = 'cache+memcached://127.0.0.1:11213/'
BROKER_URL = 'amqp://guest:guest@localhost:5672//'
CELERY_CACHE_BACKEND = 'celery_results'
CELERY_DEFAULT_QUEUE = 'default'
CELERY_QUEUES = (
    Queue('default', routing_key='default'),
    Queue('requests', routing_key='requests', queue_arguments={'x-message-ttl': 60}),
    Queue('writeback', routing_key='writeback', queue_arguments={'x-message-ttl': 60}),
    Queue('statistics', routing_key='statistics', queue_arguments={'x-message-ttl': 240}),
)

#CELERYBEAT_SCHEDULER = "djcelery.schedulers.DatabaseScheduler"
CELERYBEAT_SCHEDULE = {
    "updateStats": {
        "task": "ittc.cache.tasks.taskUpdateStats",
        "schedule": crontab(minute='*/1'),
        "args": (),
    },
}

# Tile Request Logs
LOG_REQUEST_ROOT = BASE_DIR+'/logs/requests'
LOG_INDIRECT_ROOT = BASE_DIR+'/logs/indirect'
LOG_ERRORS_ROOT = BASE_DIR+'/logs/errors'
LOG_REQUEST_FORMAT = '{status}	{tileorigin}	{tilesource}	{z}	{x}	{y}	{ip}	{datetime}'
LOG_REQUEST_COLLECTION = 'logs'
MONGO_AGG_FLAG = False
ASYNC_STATS = True
ASYNC_WRITEBACK = False

# Tile Request Stats
STATS_REQUEST_FILE = "stats.json"
STATS_SAVE_FILE = True
STATS_SAVE_MEMORY = False

CUSTOM_STATS = [
    {'name': 'total', 'collection': 'stats_total', 'attributes': []},
    #{'name': 'by_ip', 'collection': 'stats_by_ip', 'attributes': ['ip']},
    {'name': 'by_origin', 'collection': 'stats_by_origin', 'attributes': ['origin']},
    {'name': 'by_source', 'collection': 'stats_by_source', 'attributes': ['source']},
    #{'name': 'by_location', 'collection': 'stats_by_location', 'attributes': ['location']},
    {'name': 'by_zoom', 'collection': 'stats_by_zoom', 'attributes': ['z']},
    {'name': 'by_status', 'collection': 'stats_by_status', 'attributes': ['status']},
    {'name': 'by_year', 'collection': 'stats_by_year', 'attributes': ['year']},
    {'name': 'by_month', 'collection': 'stats_by_month', 'attributes': ['month']},
    {'name': 'by_date', 'collection': 'stats_by_date', 'attributes': ['date']},


    {'name': 'by_year_origin', 'collection': 'stats_by_year_origin', 'attributes': ['year', 'origin']},
    {'name': 'by_year_source', 'collection': 'stats_by_year_source', 'attributes': ['year', 'source']},
    {'name': 'by_date_origin', 'collection': 'stats_by_date_origin', 'attributes': ['date', 'origin']},
    {'name': 'by_date_source', 'collection': 'stats_by_date_source', 'attributes': ['date', 'source']},
    #{'name': 'by_ip_source', 'collection': 'stats_by_ip_source', 'attributes': ['ip', 'source']},
    {'name': 'by_origin_status', 'collection': 'stats_by_origin_status', 'attributes': ['origin', 'status']},
    {'name': 'by_source_status', 'collection': 'stats_by_source_status', 'attributes': ['source', 'status']},
    {'name': 'by_month_origin', 'collection': 'stats_by_month_origin', 'attributes': ['month', 'origin']},
    {'name': 'by_month_source', 'collection': 'stats_by_month_source', 'attributes': ['month', 'source']},
    {'name': 'by_zoom_status', 'collection': 'stats_by_zoom_status', 'attributes': ['z', 'status']},
    #{'name': 'by_origin_zoom_status', 'collection': 'stats_by_origin_zoom_status', 'attributes': ['origin', 'z', 'status']},
    #{'name': 'by_source_zoom_status', 'collection': 'stats_by_source_zoom_status', 'attributes': ['source', 'z', 'status']},
    #{'name': 'by_date_location', 'collection': 'stats_by_date_location', 'attributes': ['date', 'location']},
    #{'name': 'by_origin_location', 'collection': 'stats_by_origin_location', 'attributes': ['origin', 'location']},
    #{'name': 'by_source_location', 'collection': 'stats_by_source_location', 'attributes': ['source', 'location']},
    #{'name': 'by_origin_date_location', 'collection': 'stats_by_origin_date_location', 'attributes': ['origin', 'date', 'location']},
    #{'name': 'by_source_date_location', 'collection': 'stats_by_source_date_location', 'attributes': ['source', 'date', 'location']},
]

TILEJET_LIST_STATS = CUSTOM_STATS
TILEJET_COLLECTION_LOGS = LOG_REQUEST_COLLECTION
TILEJET_DBHOST = 'localhost'
#TILEJET_DBHOST = '/tmp/mongodb-27017.sock'
TILEJET_DBPORT = 27017
#TILEJET_DBPORT = None
TILEJET_DBNAME = 'tilejet'
TILEJET_LOGS_REQUEST_ROOT = LOG_REQUEST_ROOT

TILEJET_GEVENT_MONKEY_PATCH=True
