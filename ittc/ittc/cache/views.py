import json, os, datetime

from django.shortcuts import render_to_response, get_object_or_404, render
from django.template.loader import render_to_string
from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext, loader
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.conf import settings
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.core.cache import cache, caches, get_cache

import StringIO
from PIL import Image, ImageEnhance
import umemcache

from ittc.capabilities.models import TileService
from ittc.utils import bbox_intersects, bbox_intersects_source, webmercator_bbox, flip_y, bing_to_tms, tms_to_bing, tms_to_bbox, getYValues, TYPE_TMS, TYPE_TMS_FLIPPED, TYPE_BING, TYPE_WMS, getNearbyTiles, getParentTiles, getChildrenTiles, check_cache_availability, getTileFromCache, logTileRequest, getIPAddress, stats_tilerequest, tms_to_geojson
from ittc.source.models import TileSource
from ittc.cache.tasks import taskRequestTile
import json
#from ittc.cache.models import Tile

from geojson import Polygon, Feature, FeatureCollection, GeometryCollection

def render(request, template='capabilities/services.html', ctx=None, contentType=None):
    if not (contentType is None):
        return render_to_response(template, RequestContext(request, ctx), content_type=contentType)
    else:
        return render_to_response(template, RequestContext(request, ctx))

def capabilities_all_xml(request, template='capabilities/capabilities_1_0_0.xml'):
    return capabilities_all(request,template,'xml')

def capabilities_all(request, template=None, extension=None):
    ctx = {'tileservices': TileService.objects.filter(serviceType__in=[TYPE_TMS,TYPE_TMS_FLIPPED]),'title':'All Tile Services', 'SITEURL': settings.SITEURL,}
    if extension=="xml":
        if template is None:
            template = 'capabilities/capabilities_1_0_0.xml'
        return render(request,template,ctx,'text/xml')
    else:
        if template is None:
            template ='capabilities/services.html'
        return render(request,template,ctx)

def capabilities_service(request, template='capabilities/capabilities_service_1_0_0.xml', slug=None):
    print settings.SITEURL
    ctx = {'tileservice': TileService.objects.get(slug=slug), 'SITEURL': settings.SITEURL, }
    return render(request,template,ctx,'text/xml')

def flush(request):
   
    tilecache = umemcache.Client(settings.CACHES['tiles']['LOCATION'])
    tilecache.connect()
    tilecache.flush_all()

    return HttpResponse("Tile cache flushed.",
                        status=400,
                        content_type="text/plain"
                        )


def stats_json(request):

    stats = stats_tilerequest()
    return HttpResponse(json.dumps(stats),
                        status=400,
                        content_type="text/plain"
                        )

def stats_tms(request, t=None, stat=None, z=None, x=None, y=None, u=None, ext=None):

    #==#
    verbose = True
    ix = None
    iy = None
    iyf = None
    iz = None


    if u:
        iz, ix, iy = bing_to_tms(u)

    elif x and y and z:
        ix = int(x)
        iy = int(y)
        iz = int(z)

    if t == "regular":
        ify = flip_y(ix,iy,iz,256,webmercator_bbox)
    else:
        ify = iy
        iy = flip_y(ix,ify,iz,256,webmercator_bbox)


    stats = stats_tilerequest()

    key = z+"/"+x+"/"+y

    if not stat:
        return None

    image = None
    if key in stats['global'][stat]:
        blue =  (256.0 * stats['global'][stat][key]) / stats['tile']['max']
        image = Image.new("RGBA", (256, 256), (0, 0, int(blue), 128) )
    else:
        image = Image.new("RGBA", (256, 256), (0, 0, 0, 0) )

    if image:
        response = HttpResponse(content_type="image/png")
        image.save(response, "PNG")
        return response
    else:
        return None

def stats_geojson(request, stat=None, z=None):

    iz = int(z)
    features = []

    if not stat:
        return None

    stats = stats_tilerequest()

    i = 0
    for key in stats['global'][stat]:
        i = i + 1
        t = key.split("/")
        tz = int(t[0])
        tx = int(t[1])
        ty = int(t[2])
        if iz == tz:
            count = stats['global'][stat][key]
            geom = tms_to_geojson(tx,ty,tz)
            props = {"x":tx,"y":ty,"z":tz,"count": count}
            features.append( Feature(geometry=GeometryCollection(geom), id=i, properties=props) )

    geojson = FeatureCollection( features )

    return HttpResponse(str(geojson),
                        status=400,
                        content_type="application/json"
                        )

def tile_tms(request, slug=None, z=None, x=None, y=None, u=None, ext=None):
    tileservice = get_object_or_404(TileService, slug=slug)

    if tileservice:
        tilesource = tileservice.tileSource
        if tilesource:
            return requestTile(request,tileservice=tileservice,tilesource=tilesource,z=z,x=x,y=y,u=u,ext=ext)
        else:
            return HttpResponse(RequestContext(request, {}), status=404)
    else:
        return HttpResponse(RequestContext(request, {}), status=404)

def requestTile(request, tileservice=None, tilesource=None, z=None, x=None, y=None, u=None, ext=None):

    now = datetime.datetime.now()
    ip = getIPAddress(request)
    #==#
    verbose = True
    ix = None
    iy = None
    iyf = None
    iz = None
    nearbyTiles = None
    parentTiles = None
    childrenTiles = None

    #if verbose:
    #    print request.path

    if u:
        iz, ix, iy = bing_to_tms(u)

    elif x and y and z:
        ix = int(x)
        iy = int(y)
        iz = int(z)

    iy, iyf = getYValues(tileservice,tilesource,ix,iy,iz)

    tile_bbox = tms_to_bbox(ix,iy,iz)

    if settings.ITTC_SERVER['heuristic']['nearby']['enabled']:
        ir = settings.ITTC_SERVER['heuristic']['nearby']['enabled']
        nearbyTiles = getNearbyTiles(ix, iy, iz, ir)
        print "Nearby Tiles"
        print nearbyTiles

    if settings.ITTC_SERVER['heuristic']['up']['enabled']:
        parentTiles = getParentTiles(ix, iy, iz)
        print "Parent Tiles"
        print parentTiles

    if settings.ITTC_SERVER['heuristic']['down']['enabled']:
        depth = settings.ITTC_SERVER['heuristic']['down']['depth']
        minZoom = settings.ITTC_SERVER['heuristic']['down']['minZoom']
        maxZoom = settings.ITTC_SERVER['heuristic']['down']['maxZoom']
        childrenTiles = getChildrenTiles(ix, iy, iz, depth, minZoom, maxZoom)
        print "Children Tiles: "+str(len(childrenTiles))
        print childrenTiles

    if nearbyTiles:
        for t in nearbyTiles:
            tx, ty, tz = t
            taskRequestTile.delay(tilesource.id, tz, tx, ty, ext)
            #taskRequestTile.delay(ts=tilesource.id, iz=tz, ix=tx, iy=ty, ext=ext)

    if parentTiles:
        for t in parentTiles:
            tx, ty, tz = t
            taskRequestTile.delay(tilesource.id, tz, tx, ty, ext)

    if childrenTiles:
        for t in childrenTiles:
            tx, ty, tz = t
            taskRequestTile.delay(tilesource.id, tz, tx, ty, ext)

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

    if returnBlankTile:
        print "responding with blank image"
        image = Image.new("RGBA", (256, 256), (0, 0, 0, 0) )
        response = HttpResponse(content_type="image/png")
        image.save(response, "PNG")
        return response

    if returnErrorTile:
        print "responding with a red image"
        image = Image.new("RGBA", (256, 256), (256, 0, 0, 256) )
        response = HttpResponse(content_type="image/png")
        image.save(response, "PNG")
        return response

    cache_available = check_cache_availability('tiles')
    tilecache = caches['tiles']

    if not cache_available:
        print "Cache not available"

    tile = None
    if cache_available and iz >= settings.ITTC_SERVER['cache']['memory']['minZoom'] and iz <= settings.ITTC_SERVER['cache']['memory']['maxZoom']:
        key = "{layer},{z},{x},{y},{ext}".format(layer=tilesource.name,x=ix,y=iy,z=iz,ext=ext)
        #tile = tilecache.get(key)
        tile = getTileFromCache(tilecache, key, True)
        if tile:
            if verbose:
                print "cache hit for "+key
                logTileRequest(tilesource, x, y, z, 'hit', now, ip)
        else:
            if verbose:
                print "cache miss for "+key
                logTileRequest(tilesource, x, y, z, 'miss', now, ip)

            if tilesource.type == TYPE_TMS:
                tile = tilesource.requestTile(ix,iy,iz,ext,True)
            elif tilesource.type == TYPE_TMS_FLIPPED:
                tile = tilesource.requestTile(ix,iyf,iz,ext,True)

            tilecache.set(key, tile)

    else:
        if verbose:
            print "cache bypass for "+tilesource.name+"/"+str(iz)+"/"+str(ix)+"/"+str(iy)
        logTileRequest(tilesource, x, y, z, 'bypass', now, ip)

        if tilesource.type == TYPE_TMS:
            tile = tilesource.requestTile(ix,iy,iz,ext,True)
        elif tilesource.type == TYPE_TMS_FLIPPED:
            tile = tilesource.requestTile(ix,iyf,iz,ext,True)

    print "Headers:"
    print tile['headers']
    image = Image.open(StringIO.StringIO(tile['data']))
    #Is Tile blank.  then band.getextrema should return 0,0 for band 4
    #Tile Cache watermarking is messing up bands
    #bands = image.split()
    #for band in bands:
    #    print band.getextrema()
    response = HttpResponse(content_type="image/png")
    image.save(response, "PNG")
    return response
