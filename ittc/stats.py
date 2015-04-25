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

#from ittc.source.models import TileSource

http_client = httplib2.Http()

def clearStats():
    client = MongoClient('localhost', 27017)
    db = client.ittc
    for stat in settings.CUSTOM_STATS:
        db.drop_collection(stat['collection'])


def reloadStats():
    clearStats()
    client = MongoClient('localhost', 27017)
    db = client.ittc
    for doc in db[settings.LOG_REQUEST_COLLECTION].find():
        stats = buildStats(doc)
        incStats(db, stats)

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

