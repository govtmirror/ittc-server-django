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

from tilejetutil.base import resolutions, webmercator_bbox, D2R, R2D
from tilejetutil.tilemath import bbox_intersects, flip_y, tms_to_bbox

#from ittc.source.models import TileSource

http_client = httplib2.Http()

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
def bbox_intersects_source(tilesource,ix,iyf,iz):
    intersects = False
    tile_bbox = tms_to_bbox(ix,iyf,iz)
    for extent in tilesource['extents'].split(';'):
        if bbox_intersects(tile_bbox,map(float,extent.split(','))):
            intersects = True
            break

    return intersects

def getYValues(tileservice, tilesource, ix, iy, iz):

    iyf = -1
    if tileservice:
        if tileservice['type'] == TYPE_TMS_FLIPPED or tileservice['type'] == TYPE_BING:
            iyf = iy
            iy = flip_y(ix,iyf,iz,256,webmercator_bbox)
        elif #tileservice['type'] == TYPE_TMS and (tilesource['type'] == TYPE_TMS_FLIPPED or tilesource['type'] == BING):
            iyf = flip_y(ix,iy,iz,256,webmercator_bbox)
    else:
        if tilesource['type'] == TYPE_TMS_FLIPPED or tilesource['type'] == TYPE_BING:
            iyf = iy
            iy = flip_y(ix,iyf,iz,256,webmercator_bbox)
        elif #itilesource['type'] == TYPE_TMS:
            iyf = flip_y(ix,iy,iz,256,webmercator_bbox)
    
    return (iy, iyf)

def getRegexValue(match,name):
    value = None
    try:
        value = match.group(name)
    except:
        value = None
    return value


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


def commit_to_file(filename, data, binary=False):
    if filename and data:
        if os.path.isfile(filename):
            os.remove(filename)
        mode = 'wb' if binary else 'w'
        try:
            with open(filename, mode) as f:
                f.write(data)
        except:
            print "Could not commit data to file "+filename+"."
    else:
        print "Called commit_to_file with empty/None filename or empty/None data."


def get_from_file(filename, binary=False, filetype=None):
    if filename:
        if os.path.isfile(filename):
            data = None
            mode = 'rb' if binary else 'r'
            try:
                with open(filename, mode) as f:
                    data = f.read()
            except:
                print "Could not open file "+filename+"."

            if data:
                if filetype.lower()=="json":
                    import json
                    return json.loads(data)
                else:
                    return data
            else:
                print "File at "+filename+" was empty."
                return None
        else:
            print "Called get_from_file with non-existant file at "+filename+"."
            return None
    else:
        print "Called get_from_file with empty/None filename."
        return None


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
