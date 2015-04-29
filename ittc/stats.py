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


def clearStats():
    # Import Gevent and monkey patch
    from gevent import monkey
    monkey.patch_all()
    # Update MongoDB
    from pymongo import MongoClient
    client = MongoClient('localhost', 27017)
    db = client.ittc
    for stat in settings.CUSTOM_STATS:
        db.drop_collection(stat['collection'])

def reloadStats():
    print "Reloading Stats"
    # Import Gevent and monkey patch
    from gevent import monkey
    monkey.patch_all()
    # Update MongoDB
    from pymongo import MongoClient
    client = MongoClient('localhost', 27017)
    db = client.ittc
    #Clear Stats
    for stat in settings.CUSTOM_STATS:
        db.drop_collection(stat['collection'])
    # Reload Stats
    logs = db[settings.LOG_REQUEST_COLLECTION]
    stats = []
    for desc in settings.CUSTOM_STATS:
        attributes = {}
        for a in desc['attributes']:
            attributes[a] = "$"+a
        stat = {'name': desc['name'],'collection': desc['collection'], 'attributes': attributes}
        stats.append(stat)
    # Calculate Statistics
    values = []
    for stat in stats:
        print stat['name']
        if len(stat['attributes']) == 0:
            doc = {u'stat': stat['name'], u'value': logs.count()}
            db[stat['collection']].insert(doc)
        else:
            query = [
                { "$group": {
                    "_id": stat['attributes'],
                    "value": {
                        "$sum": 1
                    }
                }}
            ]
            agg = logs.aggregate(query)
            values = None
            if settings.MONGO_AGG_FLAG:
                values = list(agg)
            else:
                if u'ok' in agg and u'result' in agg and len(agg[u'result']) == 0:
                    doc = {u'stat': stat['name'], u'value': agg[u'result'][0][u'value']}
                    doc.update(agg[u'result'][0][u'_id'])
                    db[stat['collection']].insert(doc)
                else:
                    values = list(agg[u'result'])

            if values:
                docs = []
                for v in values:
                    doc = {u'stat': stat['name'], u'value': v[u'value']}
                    doc.update(v[u'_id'])
                    docs.append(doc)
                db[stat['collection']].insert(docs, continue_on_error=False)


def reloadStatsOld():
    # Import Gevent and monkey patch
    from gevent import monkey
    monkey.patch_all()
    # Update MongoDB
    from pymongo import MongoClient
    client = MongoClient('localhost', 27017)
    db = client.ittc
    #Clear Stats
    for stat in settings.CUSTOM_STATS:
        db.drop_collection(stat['collection'])
    # Reload Stats
    docs = db[settings.LOG_REQUEST_COLLECTION].find()
    #Aggregate stats in memory, sorted by collection
    totalstats_py = {}
    print "Number of Tile Requests: "+str(docs.count())
    try:
        for doc in docs:
            for s in buildStats(doc):
                match = False
                if not (s['collection'] in totalstats_py):
                    totalstats_py[s['collection']] = []
                for ts in totalstats_py[s['collection']]:
                    diff = set(s['attributes'].items()) - set(ts['attributes'].items())
                    if len(diff) == 0:
                        ts['value'] = ts['value'] + 1
                        match = True
                        break

                if not match:
                    totalstats_py[s['collection']].append({'attributes': s['attributes'], 'value': 1})

    except Exception, err:
        print "##################################"
        print "Error:"
        print err
        return

    # Flatten / add values to attributes
    totalstats_mongo = {}
    for c in totalstats_py:
        totalstats_mongo[c] = []
        for ts in totalstats_py[c]:
            a = ts['attributes']
            a['value'] = ts['value']
            totalstats_mongo[c].append(a)

    # Write to MongoDB
    for c in totalstats_mongo:
        try:
            (db[c]).insert(totalstats_mongo[c], continue_on_error=False) 
        except Exception, err:
            print err


def buildStats(r):
    stats = []
    #stats.append({'stat':'total.count', 'collection': 'stats_total', 'attributes': []})#name= total.count
    for desc in settings.CUSTOM_STATS:
        stat = {'collection': desc['collection'], 'attributes': {'stat': desc['name']}}
        for attribute in desc['attributes']:
            stat['attributes'][attribute] = r[attribute]
        stats.append(stat)
    return stats


def incStats(db, stats):
    for stat in stats:
        incStat(db[stat['collection']], stat['attributes']) 


def incStat(collection, attributes):
    #stat = collection.find_one({'stat': name})
    collection.update(attributes, {'$set': attributes, '$inc': {'value': 1}}, upsert=True)


def getStat(collection, name, fallback):
    if not collection:
        return fallback
    
    doc = collection.find_one({'stat': name})

    if doc:
        return doc['value']
    else:
        return fallback

def getStats(collection, fallback):
    if not collection:
        return fallback

    docs = collection.find()

    if docs:
        return docs
    else:
        return fallback

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

