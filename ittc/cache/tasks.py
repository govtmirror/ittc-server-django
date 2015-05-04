from __future__ import absolute_import

from django.conf import settings
from django.shortcuts import render_to_response, get_object_or_404, render

from celery import shared_task

#import umemcache

from tilejetutil.tilemath import tms_to_bbox, flip_y

from ittc.utils import bbox_intersects_source, TYPE_TMS, TYPE_TMS_FLIPPED, TYPE_BING, TYPE_WMS, commit_to_file
from ittc.source.models import TileSource
from ittc.source.utils import getTileSources

from tilejetstats.mongodb import getStat, getStats
from tilejetcache.cache import getTileFromCache, commit_to_cache

import os
import datetime

@shared_task
def taskRequestTile(ts, iz, ix, iy, ext):

    verbose = True
    now = datetime.datetime.now()
    # Load Logging Info
    #log_root = settings.LOG_REQUEST_ROOT
    log_format = settings.LOG_REQUEST_FORMAT
    #if log_root and log_format:
    #    if not os.path.exists(log_root):
    #        os.makedirs(log_root)

    #if settings.LOG_ERRORS_ROOT
    #    if not os.path.exists(log_root):
    #        os.makedirs(log_root)

    indirect_file = settings.LOG_INDIRECT_ROOT+os.sep+"requests_tiles_"+now.strftime('%Y-%m-%d')+"_indirect.tsv"
    # Find TileSource
    tilesource = None
    tilesources = getTileSources(proxy=True)
    for candidate in tilesources:
        if candidate.id == ts:
            tilesource = candidate
            break

    if not tilesource:
        error_file = settings.LOG_ERRORS_ROOT+os.sep+"requests_tiles_"+now.strftime('%Y-%m-%d')+"_errors.txt"
        with open(error_file,'a') as f:
            line = "Error: Could not find tilesource for primary key "+str(ts)+"."
            f.write(line+"\n")
        return

    #Y is always in regualar TMS before being added to task queue
    iyf = flip_y(ix,iy,iz)
    #iy, iyf = getYValues(None,tilesource,ix,iy,iz)

    tile_bbox = tms_to_bbox(ix,iy,iz)

    #Check if requested tile is within source's extents
    returnBlankTile = False
    returnErrorTile = False
    intersects = True
    if tilesource.extents:
        intersects = bbox_intersects_source(tilesource,ix,iyf,iz)
        if not intersects:
           returnBlankTile = True

    validZoom = 0
    #Check if inside source zoom levels
    if tilesource.minZoom or tilesource.maxZoom:
        if (tilesource.minZoom and iz < tilesource.minZoom):
            validZoom = -1
        elif (tilesource.maxZoom and iz > tilesource.maxZoom):
           validZoom = 1

        if validZoom != 0:
            #returnBlank = True
            returnErrorTile = True

    if returnBlankTile or returnErrorTile:
        return

    tile = None
    if iz >= settings.TILE_ACCELERATOR['cache']['memory']['minZoom'] and iz <= settings.TILE_ACCELERATOR['cache']['memory']['maxZoom']:
        #key = "{layer},{z},{x},{y},{ext}".format(layer=tilesource.name,x=ix,y=iy,z=iz,ext=ext)
        key = ",".join([tilesource.name,str(iz),str(ix),str(iy),ext])
        tilecache, tile = getTileFromCache(
            settings.CACHES['tiles']['LOCATION'],
            settings.CACHES['tiles'],
            'tiles',
            key,
            True,
            GEVENT_MONKEY_PATCH=True)


        if not tilecache:
            error_file = settings.LOG_ERRORS_ROOT+os.sep+"requests_tiles_"+now.strftime('%Y-%m-%d')+"_errors.txt"
            with open(error_file,'a') as f:
                line = "Error: Could not connect to cache (tiles)."
                f.write(line+"\n")
            return

        if tile:
            if verbose:
                print "task / cache hit for "+key
        else:
            if verbose:
                print "task / cache miss for "+key

            with open(indirect_file,'a') as f:
                line = log_format.format(
                    status='indirect',
                    tileorigin=tilesource.origin.name,
                    tilesource=tilesource.name,
                    z=iz,x=ix,y=iy,
                    ip='-',
                    datetime=now.isoformat())
                f.write(line+"\n")

            from urllib2 import HTTPError
            try:
                if tilesource.type == TYPE_TMS:
                    tile = tilesource.requestTile(ix,iy,iz,ext,True)
                elif tilesource.type == TYPE_TMS_FLIPPED:
                    tile = tilesource.requestTile(ix,iyf,iz,ext,True)
            except HTTPError, err:
                error_file = settings.LOG_ERRORS_ROOT+os.sep+"requests_tiles_"+now.strftime('%Y-%m-%d')+"_errors.txt"
                with open(error_file,'a') as f:
                    line = "Error: HTTPError.  Could not get tile ("+key+") from source."
                    f.write(line+"\n")
                return
            except:
                error_file = settings.LOG_ERRORS_ROOT+os.sep+"requests_tiles_"+now.strftime('%Y-%m-%d')+"_errors.txt"
                with open(error_file,'a') as f:
                    line = "Error: Unknown Error for tile ("+key+")."
                    f.write(line+"\n")
                return

            tilecache.set(key, tile)


@shared_task
def taskWriteBackTile(key, headers, data):
    now = datetime.datetime.now()
    tilecache, tile = getTileFromCache(
        settings.CACHES['tiles']['LOCATION'],
        settings.CACHES['tiles'],
        'tiles',
        key,
        True,
        GEVENT_MONKEY_PATCH=True)
    if not tilecache:
        #log_root = settings.LOG_ERRORS_ROOT
        #if log_root:
        #    if not os.path.exists(log_root):
        #        os.makedirs(log_root)
        error_file = settings.LOG_ERRORS_ROOT+os.sep+"requests_tiles_"+now.strftime('%Y-%m-%d')+"_errors.txt"
        with open(error_file,'a') as f:
            line = "Error: Could not connect to cache (tiles)."
            f.write(line+"\n")
        return
    # Double check that another thread didn't writeback already
    if not tile:
        from json import loads
        from base64 import b64decode
        tile = {
            'headers': loads(headers),
            'data': b64decode(data)
        }
        tilecache.set(key, tile)


@shared_task
def taskIncStats(stats):
    now = datetime.datetime.now()
    # Import Gevent and monkey patch
    from gevent import monkey
    monkey.patch_all()
    # Update MongoDB
    from pymongo import MongoClient
    client = None
    db = None
    try:
        #client = MongoClient('localhost', 27017)
        client = MongoClient('/tmp/mongodb-27017.sock')
        db = client.ittc
    except:
        client = None
        db = None
        errorline = "Error: Could not connet to stats database from taskIncStats. Most likely issue with connection pool"
        error_file = settings.LOG_ERRORS_ROOT+os.sep+"requests_tiles_"+now.strftime('%Y-%m-%d')+"_errors.txt"
        with open(error_file,'a') as f:
            f.write(errorline+"\n")

    # Increment Statistics
    if client and db:
        for stat in stats:
            try:
                collection = db[stat['collection']]
                collection.update(stat['attributes'], {'$set': stat['attributes'], '$inc': {'value': 1}}, upsert=True, w=0)
            except:
                errorline = "Error: Could not connect to upsert stats from taskIncStats.  Most likely issue with sockets"
                error_file = settings.LOG_ERRORS_ROOT+os.sep+"requests_tiles_"+now.strftime('%Y-%m-%d')+"_errors.txt"
                with open(error_file,'a') as f:
                    f.write(errorline+"\n")

@shared_task
def taskUpdateStats():
    now = datetime.datetime.now()
    stats = {}

    # Import Gevent and monkey patch
    from gevent import monkey
    monkey.patch_all()
    # Update MongoDB
    from pymongo import MongoClient
    client = None
    db = None
    try:
        #client = MongoClient('localhost', 27017)
        client = MongoClient('/tmp/mongodb-27017.sock')
        db = client.ittc
    except:
        client = None
        db = None
        errorline = "Error: Could not connet to stats database from scheduled taskUpdateStats. Most likely issue with connection pool"
        error_file = settings.LOG_ERRORS_ROOT+os.sep+"requests_tiles_"+now.strftime('%Y-%m-%d')+"_errors.txt"
        with open(error_file,'a') as f:
            f.write(errorline+"\n")

    if client and db:
        stats_total = db.stats_total
        stats = {
            'total': {
                'count': getStat(stats_total, 'total.count', 0)
            }
        }
        print stats
        for desc in settings.CUSTOM_STATS:
            name = desc['name']
            attrs = desc['attributes']

            print desc
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

        if settings.STATS_SAVE_FILE:
            import json
            commit_to_file(settings.STATS_REQUEST_FILE, json.dumps(stats), binary=False)

        if settings.STATS_SAVE_MEMORY:
            commit_to_cache('default', 'stats_tilerequests', stats, GEVENT_MONKEY_PATCH=True)
