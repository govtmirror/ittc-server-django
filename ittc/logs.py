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

from pymongo import MongoClient

from .stats import buildStats, incStats

import iso8601

#from ittc.source.models import TileSource

http_client = httplib2.Http()


def clearLogs():
    client = MongoClient('localhost', 27017)
    db = client.ittc
    db.drop_collection(settings.LOG_COLLECTION)

def reloadLogs():
    clearLogs()
    if settings.LOG_ROOT:
        if os.path.exists(settings.LOG_ROOT+"/"+"tile_requests.tsv"):
            with open(settings.LOG_ROOT+"/"+"tile_requests.tsv",'r') as f:
                lines =  f.readlines()
                for line in lines:
                    values = line.rstrip('\n').split("\t")
                    status = values[0]
                    tileorigin = values[1]
                    tilesource = values[2]
                    z = values[3]
                    x = values[4]
                    y = values[5]
                    ip = values[6]
                    #dt = datetime.datetime.strptime(values[6],'YYYY-MM-DDTHH:MM:SS.mmmmmm')
                    dt = iso8601.parse_date(values[7])
                    location = z+"/"+x+"/"+y
                    client = MongoClient('localhost', 27017)
                    db = client.ittc
                    r = buildTileRequestDocument(tileorigin, tilesource, x, y, z, status, dt, ip)
                    db[settings.LOG_COLLECTION].insert(r)

def buildTileRequestDocument(tileorigin, tilesource, x, y, z, status, datetime, ip):
    r = {
        'ip': ip,
        'origin': tileorigin if tileorigin else "",
        'source': tilesource,
        'location': z+'/'+x+'/'+y,
        'z': z,
        'status': status,
        'year': datetime.strftime('%Y'),
        'month': datetime.strftime('%Y-%m'),
        'date': datetime.strftime('%Y-%m-%d'),
        'date_iso': datetime.isoformat()
    }
    return r

def logTileRequest(tileorigin,tilesource, x, y, z, status, datetime, ip):
    if settings.LOG_ROOT:
        if not os.path.exists(settings.LOG_ROOT):
            os.mkdir(settings.LOG_ROOT)
        with open(settings.LOG_ROOT+"/"+"tile_requests.tsv",'a') as f:
            line = settings.LOG_FORMAT['tile_request'].format(status=status,tileorigin=tileorigin.name,tilesource=tilesource.name,z=z,x=x,y=y,ip=ip,datetime=datetime.isoformat())
            f.write(line+"\n")
            # Update MongoDB
            client = MongoClient('localhost', 27017)
            db = client.ittc
            r = buildTileRequestDocument(tileorigin.name,tilesource.name, x, y, z, status, datetime, ip)
            # Update Mongo Logs
            db[settings.LOG_COLLECTION].insert(r)
            # Update Mongo Aggregate Stats
            stats = buildStats(r)
            incStats(db, stats)
