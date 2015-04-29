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
from django.http import Http404
from django.utils.encoding import force_str, force_text, smart_text
from django.core.exceptions import ValidationError

from geojson import Polygon, Feature, FeatureCollection, GeometryCollection

from urlparse import urlparse

import json

from .stats import buildStats, incStats

#from ittc.source.models import TileSource

http_client = httplib2.Http()

resolutions = [
    156543.03390000000945292413,
    78271.51695000000472646207,
    39135.75847500000236323103,
    19567.87923750000118161552,
    9783.93961875000059080776,
    4891.96980937500029540388,
    2445.98490468750014770194,
    1222.99245234375007385097,
    611.49622617187503692548,
    305.74811308593751846274,
    152.87405654296875923137,
    76.43702827148437961569,
    38.21851413574218980784,
    19.10925706787109490392,
    9.55462853393554745196,
    4.77731426696777372598,
    2.38865713348388686299,
    1.19432856674194343150,
    0.59716428337097171575,
    0.29858214168548585787,
    0.14929107084274292894,
    0.07464553542137146447
]

webmercator_bbox = [-20037508.34,-20037508.34,20037508.34,20037508.34]

D2R = math.pi / 180,
R2D = 180 / math.pi;

TYPE_TMS = 1
TYPE_TMS_FLIPPED = 2
TYPE_BING = 3
TYPE_WMS = 4

TYPE_CHOICES = [
  (TYPE_TMS, _("TMS")),
  (TYPE_TMS_FLIPPED, _("TMS - Flipped")),
  (TYPE_BING, _("Bing")),
  (TYPE_WMS, _("WMS"))
]

IMAGE_EXTENSION_CHOICES = [
  ('png', _("png")),
  ('gif', _("gif")),
  ('jpg', _("jpg")),
  ('jpeg', _("jpeg"))
]


#===================================#

def bbox_to_wkt(x0, x1, y0, y1, srid="4326"):
    if None not in [x0, x1, y0, y1]:
        wkt = 'SRID=%s;POLYGON((%s %s,%s %s,%s %s,%s %s,%s %s))' % (
            srid, x0, y0, x0, y1, x1, y1, x1, y0, x0, y0)
    else:
        wkt = 'SRID=4326;POLYGON((-180 -90,-180 90,180 90,180 -90,-180 -90))'
    return wkt

def llbbox_to_mercator(llbbox):
    minlonlat = forward_mercator([llbbox[0], llbbox[1]])
    maxlonlat = forward_mercator([llbbox[2], llbbox[3]])
    return [minlonlat[0], minlonlat[1], maxlonlat[0], maxlonlat[1]]


def mercator_to_llbbox(bbox):
    minlonlat = inverse_mercator([bbox[0], bbox[1]])
    maxlonlat = inverse_mercator([bbox[2], bbox[3]])
    return [minlonlat[0], minlonlat[1], maxlonlat[0], maxlonlat[1]]


def forward_mercator(lonlat):
    """
        Given geographic coordinates, return a x,y tuple in spherical mercator.

        If the lat value is out of range, -inf will be returned as the y value
    """
    x = lonlat[0] * 20037508.34 / 180
    try:
        # With data sets that only have one point the value of this
        # expression becomes negative infinity. In order to continue,
        # we wrap this in a try catch block.
        n = math.tan((90 + lonlat[1]) * math.pi / 360)
    except ValueError:
        n = 0
    if n <= 0:
        y = float("-inf")
    else:
        y = math.log(n) / math.pi * 20037508.34
    return (x, y)

def bbox_intersects(a,b):
    #print "A: "+str(a)
    #print "B: "+str(b)
    return ( a[0] < b[2] and a[2] > b[0] ) and ( a[1] < b[3] and a[3] > b[1] )

def bbox_intersects_source(tilesource,ix,iyf,iz):
    intersects = False
    tile_bbox = tms_to_bbox(ix,iyf,iz)
    for extent in tilesource.extents.split(';'):
        if bbox_intersects(tile_bbox,map(float,extent.split(','))):
            intersects = True
            break

    return intersects

def getMaxX(res, size, bbox):
    maxX = int(
        round(
            (bbox[2] - bbox[0]) /
            (res * size)
        )
    ) - 1
    return maxX

def getMaxY(res, size, bbox):
    maxY = int(
        round(
            (bbox[3] - bbox[1]) /
            (res * size)
        )
    ) - 1
    return maxY

# Flipping in both directions is the same equation
def flip_y(x,y,z,size=256,bbox=[-20037508.34,-20037508.34,20037508.34,20037508.34]):
    res = resolutions[int(z)]
    maxY = int(
        round(
            (bbox[3] - bbox[1]) / 
            (res * size)
        )
    ) - 1
    return maxY - y

def tms_to_bbox(x,y,z):
    e = tile_to_lon(x+1,z)
    w = tile_to_lon(x,z)
    s = tile_to_lat(y+1,z)
    n = tile_to_lat(y,z)
    return [w, s, e, n]

def tms_to_geojson(x,y,z):
    bbox = tms_to_bbox(x,y,z)
    minx = bbox[0]
    miny = bbox[1]
    maxx = bbox[2]
    maxy = bbox[3]
    geom = Polygon([[(minx,miny),(maxx,miny),(maxx,maxy),(minx,maxy),(minx,miny)]])
    return geom


def tile_to_lon(x, z):
    return (x/math.pow(2,z)*360-180);


def tile_to_lat(y, z):
    n = math.pi - 2 * math.pi * y / math.pow(2,z);
    return ( R2D * math.atan(0.5*(math.exp(n)-math.exp(-n))));

def tms_to_bing(x,y,z):
    quadKey = []
    for i in range(z,0,-1):
        digit = 0
        mask = 1 << ( i - 1)
        if ((x & mask) != 0):
            digit += 1
        if ((y & mask) != 0):
            digit += 1
            digit += 1
        quadKey.push(digit);

    return ''.join(quadKey);

#u shold be a string represetnation of the quadkey digit
def bing_to_tms(u):
    iz = len(u)
    ix = getXCoordFromQuadKey(u)
    iy = getYCoordFromQuadKey(u)
    return iz, ix, iy


#http://www.simplehooman.co.uk/2012/09/convert-quadtree-to-tms-or-zxy/
def getXCoordFromQuadKey(u):
    x = 0
    for i in range(0,len(u)):
        x = x * 2
        if ( int(u[i]) == 1 ) or ( int(u[i]) == 3 ):
            x += 1
    return x

def getYCoordFromQuadKey(u):
    y = 0
    for i in range(0,len(u)):
        y = y * 2
        if ( int(u[i]) == 2 ) or ( int(u[i]) == 3 ):
            y += 1
    return y

def getYValues(tileservice, tilesource, ix, iy, iz):

    if tileservice:
        if tileservice.type == TYPE_TMS_FLIPPED or tileservice.type == TYPE_BING:
            iyf = iy
            iy = flip_y(ix,iyf,iz,256,webmercator_bbox)
        elif tileservice.type == TYPE_TMS and tilesource.type == TYPE_TMS_FLIPPED:
            iyf = flip_y(ix,iy,iz,256,webmercator_bbox)
    else:
        if tilesource.type == TYPE_TMS_FLIPPED:
            iyf = iy
            iy = flip_y(ix,iyf,iz,256,webmercator_bbox)
        elif tilesource.type == TYPE_TMS:
            iyf = flip_y(ix,iy,iz,256,webmercator_bbox)
    
    return iy, iyf

def getRegexValue(match,name):
    value = None
    try:
        value = match.group(name)
    except:
        value = None
    return value

def getNearbyTiles(ix0, iy0, iz0, ir, size=256, bbox=[-20037508.34,-20037508.34,20037508.34,20037508.34]):
    nearbyTiles = []

    if iz0 == 0:
        return nearbyTiles

    res = resolutions[int(iz0)]
    maxX = getMaxX(res, size, bbox)
    maxY = getMaxY(res, size, bbox)

    for iy1 in range(iy0-ir,iy0+ir+1):
        for ix1 in range(ix0-ir,ix0+ir+1):
            if iy1 != iy0 or ix1 != ix0:
                iy1 = iy1 % maxY
                ix1 = ix1 % maxX
                t = (ix1, iy1, iz0)
                nearbyTiles.append(t)

    return nearbyTiles

def getParentTiles(ix0, iy0, iz0, depth=-1, size=256, bbox=[-20037508.34,-20037508.34,20037508.34,20037508.34]):
    parentTiles = []

    res = resolutions[int(iz0)]
    maxX = getMaxX(res, size, bbox)
    maxY = getMaxY(res, size, bbox)

    levels = range(iz0-depth, iz0) if depth != -1 else range(0, iz0)
    #print levels
    for iz1 in levels:
        ix1 = int(ix0 / math.pow(2, iz0-iz1))
        iy1 = int(iy0 / math.pow(2, iz0-iz1))
        t = (ix1, iy1, iz1)
        parentTiles.append(t)

    return parentTiles

def getChildrenTiles(ix0, iy0, iz0, depth, minZoom, maxZoom, size=256, bbox=[-20037508.34,-20037508.34,20037508.34,20037508.34]):
    childrenTiles = []

    res = resolutions[int(iz0)]
    maxX = getMaxX(res, size, bbox)
    maxY = getMaxY(res, size, bbox)

    iz1 = max(iz0, minZoom)
    t = (ix0, iy0, iz1)
    d1 = depth-(iz1-iz0)
    childrenTiles = nav_down([], t, d1, maxZoom)
    return childrenTiles

def nav_down(tiles, t, d, max):
    x, y, z = t
    if z == max or d <= 0:
        tiles.append(t)
        return tiles
    else:
        t00 = x * 2, y * 2, z + 1
        t01 = x * 2, y * 2 + 1, z +1
        t10 = x * 2 + 1, y * 2, z + 1
        t11 =  x * 2 + 1, y * 2 + 1, z + 1
        tiles = nav_down(tiles, t00, d-1, max)
        tiles = nav_down(tiles, t01, d-1, max)
        tiles = nav_down(tiles, t10, d-1, max)
        tiles = nav_down(tiles, t11, d-1, max)
        return tiles

def getValue(d, name, fallback=None):
    value = None
    if d:
        try:
            value = d[name]
        except KeyError:
            value = fallback
    else:
        value = fallback
    return value

def check_cache_availability(cache):
    available = False
    from django.core.cache import caches
    tilecache = caches[cache]
    try:
        tilecache.get('')
        available = True
    except:
        available = False
    return available


def connect_to_cache(name):
    # Import Gevent and monkey patch
    from gevent import monkey
    monkey.patch_all()
    # Import Django Cache (mozilla/django-memcached-pool)
    #from django.core.cache import cache, caches, get_cache
    #from django.core.cache import caches
    # Get Tile Cache
    cache = None
    try:
        from memcachepool.cache import UMemcacheCache
        cache = UMemcacheCache(settings.CACHES[name]['LOCATION'], {})
        cache.get('')
    except:
        cache = None
    return cache


def get_from_cache(name, key):
    # Import Gevent and monkey patch
    from gevent import monkey
    monkey.patch_all()
    # Import Django Cache (mozilla/django-memcached-pool)
    #from django.core.cache import cache, caches, get_cache
    #from django.core.cache import caches
    # Get Tile Cache
    cache = None
    obj = None
    try:
        from memcachepool.cache import UMemcacheCache
        cache = UMemcacheCache(settings.CACHES[name]['LOCATION'], settings.CACHES[name]['OPTIONS'])
        #cache = caches['tiles']
    except:
        cache = None

    if cache:
        try:
            obj = cache.get(key)
        except:
            obj = None
    return (cache, obj)


def commit_to_cache(name, key, obj):
    # Import Gevent and monkey patch
    from gevent import monkey
    monkey.patch_all()
    # Import Django Cache (mozilla/django-memcached-pool)
    #from django.core.cache import cache, caches, get_cache
    #from django.core.cache import caches
    # Get Tile Cache
    cache = None
    success = False
    try:
        from memcachepool.cache import UMemcacheCache
        cache = UMemcacheCache(settings.CACHES[name]['LOCATION'], settings.CACHES[name]['OPTIONS'])
        #cache = caches['tiles']
    except:
        cache = None

    if cache:
        try:
            cache.set(key, obj)
            success = True
        except:
            success = False
    return success


#How to parse HTTP Expires header
#http://stackoverflow.com/questions/1471987/how-do-i-parse-an-http-date-string-in-python
def check_tile_expired(tile):
    expired = False
    now = datetime.datetime.now()
    #print "Now"
    #print now
    headers = tile['headers']
    if getValue(headers,'Expires'):
        #time_expires = datetime.datetime.strptime(getHeader(headers,'Expires'), "%a, %d-%b-%Y %H:%M:%S GMT")
        time_expires = datetime.datetime(*eut.parsedate(getValue(headers,'Expires'))[:6])
        #print "Time Expires"
        #print time_expires
        if now >= time_expires:
            expired = True

    return expired

def getTileFromCache(name, key, check):
    tilecache, tile = get_from_cache(name, key)
    if not tile:
        return tilecache, None

    if check:
        if check_tile_expired(tile):
            print "Tile is expired.  Evicting and returning None"
            tilecache.delete(tile)
            return tilecache, None

    return tilecache, tile


def getIPAddress(request):
    ip = None
    #print request.META['HTTP_X_FORWARDED_FOR']
    try:
        ip = request.META['HTTP_X_FORWARDED_FOR']
    except:
        ip = None
    return ip

def logs_tilerequest(mongo=True):
    logs = {
        'logs':[]
    }
    if mongo:
        # Import Gevent and monkey patch
        from gevent import monkey
        monkey.patch_all()
        # Update MongoDB
        from pymongo import MongoClient
        #client = MongoClient('localhost', 27017)
        client = MongoClient('/tmp/mongodb-27017.sock')
        db = client.ittc
        collection = db[settings.LOG_COLLECTION]
        for doc in collection.find():
            #Filter out IP Addresses and other info
            out = {
              'source': doc.source,
              'location': doc.location,
              'z': doc.z,
              'status': doc.status,
              'year': doc.year,
              'month': doc.month,
              'date': doc.date,
              'date_iso': doc.date_iso
            }
            logs['logs'].append(out)

    return logs

def formatMemorySize(num, original='B', suffix='B'):
    units = ['','K','M','G','T','P','E','Z']
    if original!='B':
        units = units[units.index(original.upper()):]
    for unit in units:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'YB', suffix)


def url_to_pattern(url, extensions=['png','gif','jpg','jpeg']):
    o = urlparse(url)
    pattern = o.scheme + "://" + o.netloc + o.path
    # Pattern = url without querystring
    pattern = pattern.replace('{slug}','(?P<slug>[^/]+)')
    a = ['x','y','z']
    for i in range(len(a)):
      #pattern = pattern.replace('{'+a[i]+'}','(?P<'+a[i]+'>[^/]+)')
      pattern = pattern.replace('{'+a[i]+'}','(?P<'+a[i]+'>[\\d]+)')
    pattern = pattern.replace('{ext}','(?P<ext>('+("|".join(extensions))+'))')
    return pattern


def service_to_url(base, name, extensions=['png','gif','jpg','jpeg']):
    url = base + 'cache/tms/'+name+'/{z}/{x}/{y}.png'
    return url


def string_to_list(value):
    print value
    if not value:
        return []
    else:
        print value[2:-1]
        a = value[2:-1].split(u",")
        print a
        if not isinstance(a, (list, tuple)):
            raise ValidationError('value can not be converted to list', code='invalid_list')
        else:
            return [smart_text(b[1:-1]) for b in a]
