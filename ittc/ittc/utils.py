import httplib2
import base64
import math
import copy
import string

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.core.cache import cache
from django.http import Http404

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

    if tileservice.serviceType == TYPE_TMS_FLIPPED or tileservice.serviceType == TYPE_BING:
        iyf = iy
        iy = flip_y(ix,iyf,iz,256,webmercator_bbox)
    elif tileservice.serviceType == TYPE_TMS and tilesource.type == TYPE_TMS_FLIPPED:
        ify = flip_y(ix,iy,iz,256,webmercator_bbox)

    return iy, iyf
