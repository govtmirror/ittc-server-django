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
from django.utils.encoding import force_str, force_text, smart_text
from django.core.exceptions import ValidationError

from geojson import Polygon, Feature, FeatureCollection, GeometryCollection

from urlparse import urlparse

import json

from .models import TileOrigin, TileSource


def reloadTileSources(proxy=False):
    defaultCache = caches['default']
    if proxy:
        tilesources_django = TileSource.objects.exclude(pattern__isnull=True).exclude(pattern__exact='')
        #tilesources_cache = [ {} for ts in tilesources_django]
        tilesources_cache = tilesources_django
        defaultCache.set('tilesources_proxy', tilesources_cache)
    else:
        tilesources_django = TileSource.objects.all()
        #tilesources_cache = [ {} for ts in tilesources_django]
        tilesources_cache = tilesources_django
        defaultCache.set('tilesources', tilesources_cache)


def getTileSources(proxy=False, debug=False):
    defaultCache = caches['default']
    if proxy:
        tilesources = defaultCache.get('tilesources_proxy')
        if tilesources:
            if debug:
                print "tilesources cached"
            return tilesources
        else:
            tilesources_django = TileSource.objects.exclude(pattern__isnull=True).exclude(pattern__exact='')
            #tilesources_cache = [ {} for ts in tilesources_django]
            tilesources_cache = tilesources_django
            defaultCache.set('tilesources_proxy', tilesources_cache)
            return tilesources_cache
    else:
        tilesources = defaultCache.get('tilesources')
        if tilesources:
            return tilesources
        else:
            tilesources_django = TileSource.objects.all()
            #tilesources_cache = [ {} for ts in tilesources_django]
            tilesources_cache = tilesources_django
            defaultCache.set('tilesources', tilesources_cache)
            return tilesources_cache

def reloadTileOrigins(proxy=False):
    defaultCache = caches['default']
    if proxy:
        tileorigins_django = TileOrigin.objects.exclude(pattern__isnull=True).exclude(pattern__exact='').filter(auto=True)
        #tilesources_cache = [ {} for ts in tilesources_django]
        tileorigins_cache = tileorigins_django
        defaultCache.set('tileorigins_proxy', tileorigins_cache)
    else:
        tileorigins_django = TileOrigin.objects.all()
        #tilesources_cache = [ {} for ts in tilesources_django]
        tileorigins_cache = tileorigins_django
        defaultCache.set('tileorigins', tileorigins_cache)


def getTileOrigins(proxy=False, debug=False):
    defaultCache = caches['default']
    if proxy:
        tileorigins = defaultCache.get('tileorigins_proxy')
        if tileorigins:
            if debug:
                print "tileorigins cached"
            return tileorigins
        else:
            tileorigins_django = TileOrigin.objects.exclude(pattern__isnull=True).exclude(pattern__exact='').filter(auto=True)
            #tilesources_cache = [ {} for ts in tilesources_django]
            tileorigins_cache = tileorigins_django
            defaultCache.set('tileorigins_proxy', tileorigins_cache)
            return tileorigins_cache
    else:
        tileorigins = defaultCache.get('tileorigins')
        if tileorigins:
            return tileorigins
        else:
            tileorigins_django = TileOrigin.objects.all()
            #tilesources_cache = [ {} for ts in tilesources_django]
            tileorigins_cache = tileorigins_django
            defaultCache.set('tileorigins', tileorigins_cache)
            return tileorigins_cache
