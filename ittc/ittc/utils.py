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
