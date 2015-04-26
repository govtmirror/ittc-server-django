from __future__ import absolute_import

from django.conf import settings
from django.core.cache import cache, caches, get_cache
from django.shortcuts import render_to_response, get_object_or_404, render

from celery import shared_task

import umemcache

from ittc.utils import bbox_intersects, bbox_intersects_source, webmercator_bbox, flip_y, bing_to_tms, tms_to_bing, tms_to_bbox, getYValues, TYPE_TMS, TYPE_TMS_FLIPPED, TYPE_BING, TYPE_WMS, getNearbyTiles
from ittc.source.models import TileSource

@shared_task
def taskRequestTile(ts, iz, ix, iy, ext):

    verbose = True

    tilesource = get_object_or_404(TileSource, pk=ts)
    #Y is always in regualar TMS before being added to task queue
    iyf = flip_y(ix,iy,iz)
    #iy, iyf = getYValues(None,tilesource,ix,iy,iz)

    tile_bbox = tms_to_bbox(ix,iy,iz)
    tilecache = caches['tiles']
    #tilecache = umemcache.Client(settings.CACHES['tiles']['LOCATION'])
    #tilecache.connect()

    #raise Exception(str(tilecache))

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
        return None

    tile = None
    if iz >= settings.TILE_ACCELERATOR['cache']['memory']['minZoom'] and iz <= settings.TILE_ACCELERATOR['cache']['memory']['maxZoom']:
        key = "{layer},{z},{x},{y},{ext}".format(layer=tilesource.name,x=ix,y=iy,z=iz,ext=ext)
        #raise Exception(key)
        tile = tilecache.get(key)
        #raise Exception(str(tile))
        if tile:
            if verbose:
                print "task / cache hit for "+key
        else:
            if verbose:
                print "task / cache miss for "+key

            if tilesource.type == TYPE_TMS:
                tile = tilesource.requestTile(ix,iy,iz,ext,True)
            elif tilesource.type == TYPE_TMS_FLIPPED:
                tile = tilesource.requestTile(ix,iyf,iz,ext,True)

            tilecache.set(key, tile)
