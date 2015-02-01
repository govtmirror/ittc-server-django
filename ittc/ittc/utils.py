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
        if tileservice.serviceType == TYPE_TMS_FLIPPED or tileservice.serviceType == TYPE_BING:
            iyf = iy
            iy = flip_y(ix,iyf,iz,256,webmercator_bbox)
        elif tileservice.serviceType == TYPE_TMS and tilesource.type == TYPE_TMS_FLIPPED:
            ify = flip_y(ix,iy,iz,256,webmercator_bbox)
    else:
        if tilesource.type == TYPE_TMS_FLIPPED:
            iyf = iy
            iy = flip_y(ix,iyf,iz,256,webmercator_bbox)
        elif tilesource.type == TYPE_TMS:
            ify = flip_y(ix,iy,iz,256,webmercator_bbox)
    
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

def getParentTiles(ix0, iy0, iz0, size=256, bbox=[-20037508.34,-20037508.34,20037508.34,20037508.34]):
    parentTiles = []

    res = resolutions[int(iz0)]
    maxX = getMaxX(res, size, bbox)
    maxY = getMaxY(res, size, bbox)

    for iz1 in range(0, iz0):
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

def getHeader(headers, name):
    value = None
    try:
        value = headers[name]
    except KeyError:
        value = None
    return value

def check_cache_availability(cache):
    available = False
    tilecache = caches[cache]
    try:
        tilecache.get('')
        available = True
    except:
        available = False
    return available

#How to parse HTTP Expires header
#http://stackoverflow.com/questions/1471987/how-do-i-parse-an-http-date-string-in-python
def check_tile_expired(tile):
    expired = False
    now = datetime.datetime.now()
    print "Now"
    print now
    headers = tile['headers']
    if getHeader(headers,'Expires'):
        #time_expires = datetime.datetime.strptime(getHeader(headers,'Expires'), "%a, %d-%b-%Y %H:%M:%S GMT")
        time_expires = datetime.datetime(*eut.parsedate(getHeader(headers,'Expires'))[:6])
        print "Time Expires"
        print time_expires
        if now >= time_expires:
            expired = True

    return expired

def getTileFromCache(cache, key, check):
    if cache:
        if check:
            tile = cache.get(key)
            if tile is None:
                return None
            else:
                if check_tile_expired(tile):
                    print "Tile is expired.  Evicting and returning None"
                    cache.delete(tile)
                    return None
                else:
                    return tile
        else:
            return cache.get(key)
    else:
        return None

def getIPAddress(request):
    ip = None
    print request.META['HTTP_X_FORWARDED_FOR']
    try:
        ip = request.META['HTTP_X_FORWARDED_FOR']
    except:
        ip = None
    return ip

def logTileRequest(tilesource, x, y, z, status, datetime, ip):
    if settings.LOG_ROOT:
        if not os.path.exists(settings.LOG_ROOT):
            os.mkdir(settings.LOG_ROOT)
        with open(settings.LOG_ROOT+"/"+"tile_requests.tsv",'a') as f:
            line = settings.LOG_FORMAT['tile_request'].format(status=status,tilesource=tilesource.name,z=z,x=x,y=y,ip=ip,datetime=datetime.isoformat())
            f.write(line+"\n")


def stats_tilerequest():
    stats = {
        'total': {
            'count': 0
        },
        'tile': {
            'max': 0
        },
        'global':{
            'strict': {},
            'parents': {}
        },
        'tilesource':{}
    }
    if settings.LOG_ROOT:
        if os.path.exists(settings.LOG_ROOT+"/"+"tile_requests.tsv"):
            with open(settings.LOG_ROOT+"/"+"tile_requests.tsv",'r') as f:
                lines =  f.readlines()
                for line in lines:
                    values = line.split("\t")
                    status = values[0]
                    tilesource = values[1]
                    z = values[2]
                    x = values[3]
                    y = values[4]
                    key = z+"/"+x+"/"+y
                    total_count = stats['total']['count']
                    global_count = 0
                    source_count = 0
                    if key in stats['global']['strict']:
                        global_count = stats['global']['strict'][key]
                    if tilesource in stats['tilesource']:
                        if key in stats['tilesource'][tilesource]:
                            source_count = stats['tilesource'][tilesource][key]
                    else:
                        stats['tilesource'][tilesource] = {}
                    #==#
                    total_count += 1
                    global_count += 1
                    source_count += 1
                    stats['global']['strict'][key] = global_count
                    stats['tilesource'][tilesource][key] = source_count
                    stats['total']['count'] = total_count

                    #==#
                    #Parent Tiles
                    parentTiles = getParentTiles(int(x), int(y), int(z))
                    for pt in parentTiles:
                        px, py, pz = pt
                        key = str(pz)+"/"+str(px)+"/"+str(py)
                        if key in stats['global']['parents']:
                            stats['global']['parents'][key] = stats['global']['parents'][key] + 1
                        else:
                            stats['global']['parents'][key] = 1

    global_max = 0
    for key in stats['global']['strict']:
        if stats['global']['strict'][key] > global_max:
            global_max = stats['global']['strict'][key]
    stats['tile']['max'] = global_max

    return stats
