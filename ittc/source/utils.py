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

from ittc.cache.models import TileService

from ittc.utils import getValue, TYPE_TMS, TYPE_TMS_FLIPPED, TYPE_BING, TYPE_WMS


def reloadTileServices():
    defaultCache = caches['default']
    tileservices_django = TileService.objects.all()
    tileservices_cache = processTileServices(tileservices_django)
    defaultCache.set('tileservices', tileservices_cache)


def getTileServices(debug=False):
    defaultCache = caches['default']
    tileservices = defaultCache.get('tileservices')
    if tileservices:
        return tileservices
    else:
        tileservices_django = TileService.objects.all()
        tileservices_cache = processTileServices(tileservices_django)
        defaultCache.set('tileservices', tileservices_cache)
        return tileservices_cache


def processTileServices(tileservices_django):
    if tileservices_django:
        tileservices_cache = []
        for ts_d in tileservices_django:
            ts_c = {
                'id': ts_d.id,
                'name': ts_d.name,
                'description': ts_d.description,
                'type': ts_d.type,
                'type_title': ts_d.type_title(),
                'source': ts_d.source.name,
                'url': ts_d.url,
                'extensions': ts_d.extensions
            }
            tileservices_cache.append(ts_c)
        return tileservices_cache
    else:
        return None


def reloadTileSources(proxy=False):
    defaultCache = caches['default']
    if proxy:
        tilesources_django = TileSource.objects.exclude(pattern__isnull=True).exclude(pattern__exact='')
        #tilesources_cache = [ {} for ts in tilesources_django]
        tilesources_cache = processTileSources(tilesources_django)
        defaultCache.set('tilesources_proxy', tilesources_cache)
    else:
        tilesources_django = TileSource.objects.all()
        #tilesources_cache = [ {} for ts in tilesources_django]
        tilesources_cache = processTileSources(tilesources_django)
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
            tilesources_cache = processTileSources(tilesources_django)
            defaultCache.set('tilesources_proxy', tilesources_cache)
            return tilesources_cache
    else:
        tilesources = defaultCache.get('tilesources')
        if tilesources:
            return tilesources
        else:
            tilesources_django = TileSource.objects.all()
            #tilesources_cache = [ {} for ts in tilesources_django]
            tilesources_cache = processTileSources(tilesources_django)
            defaultCache.set('tilesources', tilesources_cache)
            return tilesources_cache


def processTileSources(tilesources_django):
    if tilesources_django:
        tilesources_cache = []
        for ts_d in tilesources_django:
            ts_c = {
                'id': ts_d.id,
                'name': ts_d.name,
                'description': ts_d.description,
                'type': ts_d.type,
                'type_title': ts_d.type_title(),
                'auto': ts_d.auto,
                'cacheable': ts_d.cacheable,
                'origin': ts_d.origin.name,
                'url': ts_d.url,
                'extensions': ts_d.extensions,
                'pattern': ts_d.pattern,
                'extents': ts_d.extents,
                'minZoom': ts_d.minZoom,
                'maxZoom': ts_d.maxZoom,
                # From origin
                'auth': ts_d.origin.auth
            }
            tilesources_cache.append(ts_c)
        return tilesources_cache
    else:
        return None


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


def make_request(url, params, auth=None, data=None, contentType=None):
    """
    Prepares a request from a url, params, and optionally authentication.
    """
    #print 'make_request'

    # Import Gevent and monkey patch
    #import gevent
    from gevent import monkey
    monkey.patch_all()

    # Import IO Libraries
    import urllib
    import urllib2

    if params:
        url = url + '?' + urllib.urlencode(params)

    #print url
    #print data
    #print auth
    #print contentType

    req = urllib2.Request(url, data=data)

    if auth:
        req.add_header('AUTHORIZATION', 'Basic ' + auth)

    if contentType:
        req.add_header('Content-type', contentType)
    else:
        if data:
            req.add_header('Content-type', 'text/xml')


    return urllib2.urlopen(req)


def requestTileFromSource(tilesource=None, x=None, y=None, z=None, u=None, ext=None, verbose=False):
    print "requestTileFromSource"
    if tilesource['type'] == TYPE_BING:
        if tilesource['auth']:
            url = tilesource['url'].format(u=u,ext=ext,auth=ts['auth'])
        else:
            url = tilesource['url'].format(u=u,ext=ext)
    else:
        if tilesource['auth']:
            url = tilesource['url'].format(x=x,y=y,z=z,ext=ext,auth=ts['auth'])
        else:
            url = tilesource['url'].format(x=x,y=y,z=z,ext=ext)


    contentType = "image/png"
    #contentType = "text/html"

    if verbose:
        print "Requesting tile from "+url

    print "URL: "+url

    params = None
    #params = {'access_token': 'pk.eyJ1IjoiaGl1IiwiYSI6IlhLWFA4Z28ifQ.4gQiuOS-lzhigU5PgMHUzw'}

    request = make_request(url=url, params=params, auth=None, data=None, contentType=contentType)

    if request.getcode() != 200:
        raise Exception("Could not fetch tile from source with url {url}: Status Code {status}".format(url=url,status=request.getcode()))

    #image = binascii.hexlify(request.read())
    #image = io.BytesIO(request.read()))
    image = request.read()
    info = request.info()
    headers = {
      'Expires': getValue(info, 'Expires', fallback='')
    }
    tile = {
        'headers': headers,
        'data': image
    }
    return tile
