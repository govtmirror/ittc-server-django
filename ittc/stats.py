import os
import sys
import httplib2
import base64
import math
import copy
import string
import datetime

import email.utils as eut

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.core.cache import cache, caches, get_cache
from django.http import Http404

from geojson import Polygon, Feature, FeatureCollection, GeometryCollection

from tilejetstats.mongodb import getStat, getStats

# Can't import for some reason
#from .utils import check_cache_availability

#from ittc.source.models import TileSource

http_client = httplib2.Http()

def check_cache_availability(cache):
    available = False
    tilecache = caches[cache]
    try:
        tilecache.get('')
        available = True
    except:
        available = False
    return available


def stats_tilerequest(mongo=True):
    stats = {}

    if mongo:
        # Import Gevent and monkey patch
        from gevent import monkey
        monkey.patch_all()
        # Update MongoDB
        from pymongo import MongoClient
        client = MongoClient('localhost', 27017)
        db = client.ittc
        stats_total = db.stats_total
        stats = {
            'total': {
                'count': getStat(stats_total, 'total.count', 0)
            }
        }
        for desc in settings.CUSTOM_STATS:
            name = desc['name']
            attrs = desc['attributes']

            if len(attrs) == 0:
                for doc in getStats(db[desc['collection']],[]):
                    stats[name] = doc['value']

            elif len(attrs) > 0:
                stats[name] = {}
                docs = getStats(db[desc['collection']],[])
                for doc in docs:
                    v = doc['value']
                    obj = stats[name]
                    for i in range(len(attrs)-1):
                        a = attrs[i]
                        try:
                            obj = obj[doc[a]]
                        except KeyError, e:
                            obj[doc[a]] = {}
                            obj = obj[doc[a]]

                    obj[doc[attrs[len(attrs)-1]]] = v

        return stats

    else:
        return stats


def stats_cache():

    import umemcache

    target = settings.TILE_ACCELERATOR['cache']['memory']['target']
    if(check_cache_availability(target)):
        location = settings.CACHES[target]['LOCATION']
        tilecache = umemcache.Client(location)
        tilecache.connect()
        stats = tilecache.stats()

        return stats
    else:
        return None


def getStatsFromMemory():
    defaultCache = caches['default']
    tilesources = defaultCache.get('tilesources_proxy')
    if tilesources:
        if debug:
            print "tilesources cached"
        return tilesources
    else:
        tilesources_django = TileSource.objects.exclude(pattern__isnull=True).exclude(pattern__exact='')
        tilesources_cache = tilesources_django
        defaultCache.set('tilesources_proxy', tilesources_cache)
        return tilesources_cache

