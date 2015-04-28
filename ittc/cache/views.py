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

from .models import TileService
from ittc.utils import bbox_intersects, bbox_intersects_source, webmercator_bbox, flip_y, bing_to_tms, tms_to_bing, tms_to_bbox, getYValues, TYPE_TMS, TYPE_TMS_FLIPPED, TYPE_BING, TYPE_WMS, getNearbyTiles, getParentTiles, getChildrenTiles, check_cache_availability, getTileFromCache, getIPAddress, tms_to_geojson, getValue, url_to_pattern, string_to_list
from ittc.source.utils import getTileOrigins, reloadTileOrigins, getTileSources, reloadTileSources
from ittc.utils import logs_tilerequest, formatMemorySize
from ittc.stats import stats_cache, stats_tilerequest, clearStats, reloadStats
from ittc.logs import clearLogs, reloadLogs, logTileRequest

from ittc.source.models import TileOrigin,TileSource
from ittc.cache.tasks import taskRequestTile, taskWriteBackTile
from ittc.cache.forms import TileOriginForm, TileSourceForm, TileServiceForm

import json
#from ittc.cache.models import Tile
from bson.json_util import dumps

from geojson import Polygon, Feature, FeatureCollection, GeometryCollection

import time

def render(request, template='capabilities/services.html', ctx=None, contentType=None):
    if not (contentType is None):
        return render_to_response(template, RequestContext(request, ctx), content_type=contentType)
    else:
        return render_to_response(template, RequestContext(request, ctx))

def capabilities_all_xml(request, template='capabilities/capabilities_1_0_0.xml'):
    return capabilities_all(request,template,'xml')

def capabilities_all(request, template=None, extension=None):
    ctx = {'tileservices': TileService.objects.filter(type__in=[TYPE_TMS,TYPE_TMS_FLIPPED]),'title':'All Tile Services', 'SITEURL': settings.SITEURL,}
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


@login_required
def flush(request):
   
    # Using raw umemcache flush_all function

    #defaultcache = umemcache.Client(settings.CACHES['default']['LOCATION'])
    #defaultcache.connect()
    #defaultcache.flush_all()

    #tilecache = umemcache.Client(settings.CACHES['tiles']['LOCATION'])
    #tilecache.connect()
    #tilecache.flush_all()

    #resultscache = umemcache.Client(settings.CACHES['tiles']['LOCATION'])
    #resultscache.connect()
    #resultscache.flush_all()

    #==#

    # Using custom clear function from https://github.com/mozilla/django-memcached-pool/blob/master/memcachepool/cache.py
    if(check_cache_availability('default')):
        defaultcache = caches['tiles']
        defaultcache.clear()

    if(check_cache_availability('tiles')):
        tilecache = caches['tiles']
        tilecache.clear()

    if(check_cache_availability('celery_results')):
        resultscache = caches['celery_results']
        resultscache.clear()

    return HttpResponse("Tile cache flushed.",
                        content_type="text/plain"
                        )

@login_required
def logs_json(request):

    logs = logs_tilerequest()
    return HttpResponse(dumps(logs),
                        content_type="application/json"
                        )


@login_required
def logs_clear(request):
    clearLogs()

    return HttpResponse("Logs cleared.",
                        content_type="text/plain"
                        )

@login_required
def logs_reload(request):
    clearLogs()
    reloadLogs()

    return HttpResponse("Logs reloaded from disk.",
                        content_type="text/plain"
                        )

def stats_clear(request):
    clearStats()

    return HttpResponse("Tile stats cleared.",
                        content_type="text/plain"
                        )

def stats_reload(request):
    reloadStats()

    return HttpResponse("Stats reloaded from MongoDB Logs.",
                        content_type="text/plain"
                        )


@login_required
def stats_json(request):

    stats = stats_tilerequest()
    return HttpResponse(json.dumps(stats),
                        content_type="application/json"
                        )

@login_required
def stats_cache_json(request):

    stats = {}

    target = settings.TILE_ACCELERATOR['cache']['memory']['target']
    if(check_cache_availability(target)):
        location = settings.CACHES[target]['LOCATION']
        tilecache = umemcache.Client(location)
        tilecache.connect()
        stats = tilecache.stats()

    return HttpResponse(json.dumps(stats),
                        content_type="application/json"
                        )



@login_required
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

def stats_dashboard(request, origin=None, source=None, date=None):
    stats = stats_tilerequest()
    dates = stats['by_date_location'].keys()
    context_dict = {
        'date': date,
        'origins': TileOrigin.objects.all().order_by('name','type'),
        'sources': TileSource.objects.all().order_by('name','type'),
        'dates': dates
    }

    try:
        context_dict['origin'] = TileOrigin.objects.get(name=origin)
    except:
        context_dict['origin'] = None

    try:
        context_dict['source'] = TileSource.objects.get(name=source)
    except:
        context_dict['source'] = None

    return render_to_response(
        "cache/stats_dashboard.html",
        RequestContext(request, context_dict))


@login_required
def stats_map(request, origin=None, source=None, date=None):
    stats = stats_tilerequest()
    dates = stats['by_date_location'].keys()
    #print stats['by_date_location'].keys()
    context_dict = {
        'date': date,
        'origins': TileOrigin.objects.all().order_by('name','type'),
        'sources': TileSource.objects.all().order_by('name','type'),
        'dates': dates
    }

    try:
        context_dict['origin'] = TileOrigin.objects.get(name=origin)
    except:
        context_dict['origin'] = None


    try:
        context_dict['source'] = TileSource.objects.get(name=source)
    except:
        context_dict['source'] = None


    return render_to_response(
        "cache/stats_map_3.html",
        RequestContext(request, context_dict))


@login_required
def stats_geojson_source(request, z=None, source=None):
    return stats_geojson(request, z=z, source=source)


@login_required
def stats_geojson(request, z=None, origin=None, source=None, date=None):

    iz = int(z)
    features = []

    stats = stats_tilerequest()

    root = None
    if origin and date:
        root = getValue(getValue(stats['by_origin_date_location'],origin),date)
    elif source and date:
        root = getValue(getValue(stats['by_source_date_location'],source),date)
    elif origin:
        root = stats['by_origin_location'][origin]
    elif source:
        root = stats['by_source_location'][source]
    elif date:
        root = stats['by_date_location'][date]
    else:
        root = stats['by_location']

    i = 0
    for key in root:
        i = i + 1
        t = key.split("/")
        tz = int(t[0])
        tx = int(t[1])
        ty = int(t[2])
        if iz == tz:
            #count = stats['global'][stat][key]
            count = root[key]
            geom = tms_to_geojson(tx,ty,tz)
            props = {"x":tx, "y":ty, "z":tz, "location": key, "count": count}
            features.append( Feature(geometry=geom, id=i, properties=props) )

    geojson = FeatureCollection( features )

    return HttpResponse(json.dumps(geojson),
                        content_type="application/json"
                        )


@login_required
def info(request):
    stats_tr = stats_tilerequest()
    stats_c = stats_cache()
    caches = []
    c = settings.TILE_ACCELERATOR['cache']['memory']

    size = int(stats_c['bytes'])
    maxsize = int(stats_c['limit_maxbytes'])
    size_percentage = str((100.0 * size) / maxsize)+"%" 

    caches.append({
        'name': 'memory',
        'enabled': c['enabled'],
        'description': c['description'],
        'type': c['type'],
        'size': formatMemorySize(size, original='B'),
        'maxsize': formatMemorySize(maxsize, original='B'),
        'size_percentage': size_percentage,
        'minzoom': c['minZoom'],
        'maxzoom': c['maxZoom'],
        'expiration': c['expiration'],
        'link_memcached': '/cache/stats/export/cache.json'
    })

    heuristics = []
    h = settings.TILE_ACCELERATOR['heuristic']['down']
    heuristics.append({
        'name': 'down',
        'enabled': h['enabled'],
        'description': h['description']
    })
    h = settings.TILE_ACCELERATOR['heuristic']['up']
    heuristics.append({
        'name': 'up',
        'enabled': h['enabled'],
        'description': h['description']
    })
    h = settings.TILE_ACCELERATOR['heuristic']['nearby']
    heuristics.append({
        'name': 'nearby',
        'enabled': h['enabled'],
        'description': h['description']
    })

    context_dict = {
        'origins': TileOrigin.objects.all().order_by('name','type'),
        'sources': TileSource.objects.all().order_by('name','type'),
        'caches': caches,
        'heuristics': heuristics,
        'hosts': settings.PROXY_ALLOWED_HOSTS
    }
    return render_to_response(
        "cache/info.html",
        RequestContext(request, context_dict))


@login_required
def origins_list(request):
    stats = stats_tilerequest()
    context_dict = {
        'origins': TileOrigin.objects.all().order_by('name','type'),
    }
    return render_to_response(
        "cache/origins_list.html",
        RequestContext(request, context_dict))


@login_required
def sources_list(request):
    stats = stats_tilerequest()
    context_dict = {
        'sources': TileSource.objects.all().order_by('name'),
    }
    return render_to_response(
        "cache/sources_list.html",
        RequestContext(request, context_dict))

@login_required
def services_list(request):
    stats = stats_tilerequest()
    context_dict = {
        'services': TileService.objects.all().order_by('name','type'),
    }
    return render_to_response(
        "cache/services_list.html",
        RequestContext(request, context_dict))

@login_required
def origins_new(request, template="cache/origins_edit.html"):

    if request.method == "POST":
        origin_form = TileOriginForm(request.POST)
        if origin_form.is_valid():
            origin_form.save()
            reloadTileOrigins(proxy=False)
            reloadTileOrigins(proxy=True)
            ###
            stats = stats_tilerequest()
            context_dict = {
                'origin_form': TileOriginForm()
            }

        return HttpResponseRedirect(reverse('origins_list',args=()))
    else:
        stats = stats_tilerequest()
        context_dict = {
            'origin_form': TileOriginForm()
        }
        return render_to_response(
            template,
            RequestContext(request, context_dict))


@login_required
def origins_edit(request, origin=None, template="cache/origins_edit.html"):

    if request.method == "POST":
        instance = TileOrigin.objects.get(name=origin)
        origin_form = TileOriginForm(request.POST,instance=instance)
        if origin_form.is_valid():
            origin_form.save()
            reloadTileOrigins(proxy=False)
            reloadTileOrigins(proxy=True)
            ###
            stats = stats_tilerequest()
            context_dict = {
                'origin': instance,
                'origin_form': TileOriginForm(instance=instance)
            }

            return HttpResponseRedirect(reverse('origins_list',args=()))

    else:
        stats = stats_tilerequest()
        instance = TileOrigin.objects.get(name=origin)
        context_dict = {
            'origin': instance,
            'origin_form': TileOriginForm(instance=instance)
        }
        return render_to_response(
            template,
            RequestContext(request, context_dict))


@login_required
def sources_new(request, origin=None, template="cache/sources_edit.html"):

    if request.method == "POST":
        source_form = TileSourceForm(request.POST)
        if source_form.is_valid():
            source_form.save()
            reloadTileSources(proxy=False)
            reloadTileSources(proxy=True)
            ###
            stats = stats_tilerequest()
            context_dict = {
                'source_form': TileSourceForm()
            }
            return HttpResponseRedirect(reverse('sources_list',args=()))
        else:
            return HttpResponse(
                'An unknown error has occured.'+json.dumps(source_form.errors),
                content_type="text/plain",
                status=401
            )

    else:
        stats = stats_tilerequest()
        source_form = None
        if origin:
            origin_object = TileOrigin.objects.get(name=origin)
            if origin_object.multiple:
                source_form = TileSourceForm(initial={'origin': origin_object, 'auto': False, 'type': origin_object.type, 'url': origin_object.url, 'extensions': [u'png']})
            else:
                source_form = TileSourceForm(initial={'origin': origin_object, 'auto': False, 'type': origin_object.type, 'url': origin_object.url, 'extensions': [u'png']})
        else:
            source_form = TileSourceForm()
        context_dict = {
            'source_form': source_form
        }
        return render_to_response(
            template,
            RequestContext(request, context_dict))

@login_required
def sources_edit(request, source=None, template="cache/sources_edit.html"):

    if request.method == "POST":
        instance = TileSource.objects.get(name=source)
        source_form = TileSourceForm(request.POST,instance=instance)
        if source_form.is_valid():
            source_form.save()
            reloadTileSources(proxy=False)
            reloadTileSources(proxy=True)
            ###
            stats = stats_tilerequest()
            context_dict = {
                'source': instance,
                'source_form': TileSourceForm(instance=instance)
            }
            return HttpResponseRedirect(reverse('sources_list',args=()))
        else:
            return HttpResponse(
                'An unknown error has occured.',
                content_type="text/plain",
                status=401
            )
    else:
        stats = stats_tilerequest()
        instance = TileSource.objects.get(name=source)
        context_dict = {
            'source': instance,
            'source_form': TileSourceForm(instance=instance)
        }
        return render_to_response(
            template,
            RequestContext(request, context_dict))


def sources_delete(request, source=None, template="cache/sources_delete.html"):

    if request.method == "POST":
        instance = TileSource.objects.get(name=source)
        if instance:
            instance.delete()
            return HttpResponseRedirect(reverse('sources_list',args=()))
        else:
            return HttpResponse(
                'Could not find source with name '+name,
                content_type="text/plain",
                status=401
            )
    else:
        stats = stats_tilerequest()
        instance = TileSource.objects.get(name=source)
        context_dict = {
            'source': instance
        }
        return render_to_response(
            template,
            RequestContext(request, context_dict))


@login_required
def services_new(request, source=None, template="cache/services_edit.html"):

    if request.method == "POST":
        service_form = TileServiceForm(request.POST)
        if service_form.is_valid():
            service_form.save()
            ###
            stats = stats_tilerequest()
            context_dict = {
                'service_form': TileServiceForm()
            }
            return HttpResponseRedirect(reverse('services_list',args=()))

    else:
        stats = stats_tilerequest()
        service_form = None
        if source:
            source_object = TileSource.objects.get(name=source)
            service_form = TileServiceForm(initial={'source': source_object, 'name': source_object.name, 'description': source_object.description, 'type': source_object.type, 'url': '/cache/tms/', 'extensions': [u'png']})
        else:
            service_form = TileServiceForm()
        context_dict = {
            'service_form': service_form
        }
        return render_to_response(
            template,
            RequestContext(request, context_dict))


@login_required
def services_edit(request, service=None, template="cache/services_edit.html"):

    if request.method == "POST":
        instance = TileService.objects.get(name=service)
        service_form = TileServiceForm(request.POST,instance=instance)
        if service_form.is_valid():
            service_form.save()
            ###
            stats = stats_tilerequest()
            context_dict = {
                'service': instance,
                'service_form': TileServiceForm(instance=instance)
            }
            return HttpResponseRedirect(reverse('services_list',args=()))
        else:
            return HttpResponse(
                'An unknown error has occured.',
                content_type="text/plain",
                status=401
            )
    else:
        stats = stats_tilerequest()
        instance = TileService.objects.get(name=service)
        context_dict = {
            'service': instance,
            'service_form': TileServiceForm(instance=instance)
        }
        return render_to_response(
            template,
            RequestContext(request, context_dict))


def services_delete(request, service=None, template="cache/services_delete.html"):

    if request.method == "POST":
        instance = TileService.objects.get(name=service)
        if instance:
            instance.delete()
            return HttpResponseRedirect(reverse('services_list',args=()))
        else:
            return HttpResponse(
                'Could not find service with name '+name,
                content_type="text/plain",
                status=401
            )
    else:
        stats = stats_tilerequest()
        instance = TileService.objects.get(name=service)
        context_dict = {
            'service': instance
        }
        return render_to_response(
            template,
            RequestContext(request, context_dict))


@login_required
def origins_json(request):
    now = datetime.datetime.now()
    dt = now
    #######
    stats = stats_tilerequest()
    origins = []
    for origin in TileOrigin.objects.all().order_by('name','type'):
        link_geojson = settings.SITEURL+'cache/stats/export/geojson/15/origin/'+origin.name+'.geojson'
        origins.append({
            'name': origin.name,
            'description': origin.description,
            'type': origin.type_title(),
            'multiple': origin.multiple,
            'auto': origin.auto,
            'url': origin.url,
            'requests_all': getValue(stats['by_origin'], origin.name,0),
            'requests_year': getValue(getValue(stats['by_year_origin'],dt.strftime('%Y')),origin.name, 0),
            'requests_month': getValue(getValue(stats['by_month_origin'],dt.strftime('%Y-%m')),origin.name, 0),
            'requests_today': getValue(getValue(stats['by_date_origin'],dt.strftime('%Y-%m-%d')),origin.name, 0),
            'link_geojson': link_geojson,
            'link_geojsonio': 'http://geojson.io/#data=data:text/x-url,'+link_geojson
        })

    return HttpResponse(json.dumps(origins),
                        content_type="application/json"
                        )



@login_required
def sources_json(request):
    now = datetime.datetime.now()
    dt = now
    #######
    stats = stats_tilerequest()
    sources = []
    for source in TileSource.objects.all().order_by('name'):
        link_geojson = settings.SITEURL+'cache/stats/export/geojson/15/source/'+source.name+'.geojson'
        link_proxy_internal = settings.SITEURL+'proxy/?url='+(source.url).replace("{ext}","png")
        link_proxy_external = ""
        if source.type in [TYPE_TMS, TYPE_TMS_FLIPPED]:
            link_proxy_external = settings.SITEURL+'cache/proxy/tms/origin/'+source.origin.name+'/source/'+source.name+'/{z}/{x}/{y}.png' 
        elif source.type == TYPE_BING:
            link_proxy_external = settings.SITEURL+'cache/proxy/bing/origin/'+source.origin.name+'/source/'+source.name+'{u}.png'
        sources.append({
            'name': source.name,
            'type': source.type_title(),
            'origin': source.origin.name,
            'url': source.url,
            'requests_all': getValue(stats['by_source'], source.name,0),
            'requests_year': getValue(getValue(stats['by_year_source'],dt.strftime('%Y')),source.name, 0),
            'requests_month': getValue(getValue(stats['by_month_source'],dt.strftime('%Y-%m')),source.name, 0),
            'requests_today': getValue(getValue(stats['by_date_source'],dt.strftime('%Y-%m-%d')),source.name, 0),\
            'link_proxy': link_proxy_internal,
            'link_id': 'http://www.openstreetmap.org/edit#?background=custom:'+link_proxy_external,
            'link_geojson': link_geojson,
            'link_geojsonio': 'http://geojson.io/#data=data:text/x-url,'+link_geojson
        })

    return HttpResponse(json.dumps(sources),
                        content_type="application/json"
                        )

@login_required
def services_json(request):
    now = datetime.datetime.now()
    dt = now
    #######
    stats = stats_tilerequest()
    services = []
    for service in TileService.objects.all().order_by('name'):
    #    link_geojson = settings.SITEURL+'cache/stats/export/geojson/15/source/'+source.name+'.geojson'
        #link_proxy = settings.SITEURL+'cache/tms/proxy/?url='+(source.url).replace("{ext}","png")
        link_proxy = service.url
        services.append({
            'name': service.name,
            'type': service.type_title(),
            'source': service.source.name,
            'url': service.url,
    #        'requests_all': getValue(stats['by_source'], source.name,0),
    #        'requests_year': getValue(getValue(stats['by_year_source'],dt.strftime('%Y')),source.name, 0),
    #        'requests_month': getValue(getValue(stats['by_month_source'],dt.strftime('%Y-%m')),source.name, 0),
    #        'requests_today': getValue(getValue(stats['by_date_source'],dt.strftime('%Y-%m-%d')),source.name, 0),\
            'link_proxy': link_proxy,
            'link_id': 'http://www.openstreetmap.org/edit#?background=custom:'+link_proxy,
    #        'link_geojson': link_geojson,
    #        'link_geojsonio': 'http://geojson.io/#data=data:text/x-url,'+link_geojson
        })

    return HttpResponse(json.dumps(services),
                        content_type="application/json"
                        )



@login_required
def tile_tms(request, slug=None, z=None, x=None, y=None, u=None, ext=None):
    tileservice = get_object_or_404(TileService, name=slug)

    if tileservice:
        tilesource = tileservice.source
        if tilesource:
            return requestTile(request,tileservice=tileservice,tilesource=tilesource,z=z,x=x,y=y,u=u,ext=ext)
        else:
            return HttpResponse(RequestContext(request, {}), status=404)
    else:
        return HttpResponse(RequestContext(request, {}), status=404)


def requestIndirectTiles(tilesource, ext, tiles):
    if tiles:
        for t in tiles:
            tx, ty, tz = t
            #taskRequestTile.delay(tilesource.id, tz, tx, ty, ext)
            args = [tilesource.id, tz, tx, ty, ext]
            #Expires handled by global queue setting
            taskRequestTile.apply_async(args=args, kwargs=None, queue="requests")


def requestTile(request, tileservice=None, tilesource=None, tileorigin=None, z=None, x=None, y=None, u=None, ext=None):

    print "requestTile"
    now = datetime.datetime.now()
    ip = getIPAddress(request)
    #==#
    if not tileorigin:
        tileorigin = tilesource.origin
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

    if tilesource.cacheable:

        if settings.TILE_ACCELERATOR['heuristic']['nearby']['enabled']:
            ir = settings.TILE_ACCELERATOR['heuristic']['nearby']['radius']
            nearbyTiles = getNearbyTiles(ix, iy, iz, ir)
            #print "Nearby Tiles"
            #print nearbyTiles

        if settings.TILE_ACCELERATOR['heuristic']['up']['enabled']:
            iDepth = getValue(settings.TILE_ACCELERATOR['heuristic']['up'],'depth')
            if iDepth:
                parentTiles = getParentTiles(ix, iy, iz, depth=iDepth)
            else:
                parentTiles = getParentTiles(ix, iy, iz)
            #print "Parent Tiles"
            #print parentTiles

        heuristic_down = settings.TILE_ACCELERATOR['heuristic']['down']
        if heuristic_down['enabled']:
            depth = heuristic_down['depth']
            minZoom = heuristic_down['minZoom']
            maxZoom = heuristic_down['maxZoom']
            childrenTiles = getChildrenTiles(ix, iy, iz, depth, minZoom, maxZoom)
            #print "Children Tiles: "+str(len(childrenTiles))
            #print childrenTiles

        requestIndirectTiles(tilesource, ext, nearbyTiles)
        requestIndirectTiles(tilesource, ext, parentTiles)
        requestIndirectTiles(tilesource, ext, childrenTiles)

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

    tile = None
    if tilesource.cacheable and iz >= settings.TILE_ACCELERATOR['cache']['memory']['minZoom'] and iz <= settings.TILE_ACCELERATOR['cache']['memory']['maxZoom']:
        key = "{layer},{z},{x},{y},{ext}".format(layer=tilesource.name,x=ix,y=iy,z=iz,ext=ext)
        tilecache, tile = getTileFromCache('tiles', key, True)
        if not tilecache:
            with open(error_file,'a') as f:
                line = "Error: Could not connect to cache (tiles)."
                f.write(line+"\n")
            return

        if tile:
            if verbose:
                print "cache hit for "+key
            logTileRequest(tileorigin, tilesource, x, y, z, 'hit', now, ip)
        else:
            if verbose:
                print "cache miss for "+key
            logTileRequest(tileorigin, tilesource, x, y, z, 'miss', now, ip)

            if tilesource.type == TYPE_TMS:
                tile = tilesource.requestTile(ix,iy,iz,ext,True)
            elif tilesource.type == TYPE_TMS_FLIPPED:
                tile = tilesource.requestTile(ix,iyf,iz,ext,True)

            from base64 import b64encode
            taskWriteBackTile.apply_async(
                args=[key, json.dumps(tile['headers']), b64encode(tile['data'])],
                kwargs=None,
                queue="writeback")
            # Using async algorithm instead of sync
            #tilecache.set(key, tile)

    else:
        if verbose:
            print "cache bypass for "+tilesource.name+"/"+str(iz)+"/"+str(ix)+"/"+str(iy)
        logTileRequest(tileorigin, tilesource, x, y, z, 'bypass', now, ip)

        if tilesource.type == TYPE_TMS:
            tile = tilesource.requestTile(ix,iy,iz,ext,True)
        elif tilesource.type == TYPE_TMS_FLIPPED:
            tile = tilesource.requestTile(ix,iyf,iz,ext,True)

    #print "Headers:"
    #print tile['headers']
    image = Image.open(StringIO.StringIO(tile['data']))
    #Is Tile blank.  then band.getextrema should return 0,0 for band 4
    #Tile Cache watermarking is messing up bands
    #bands = image.split()
    #for band in bands:
    #    print band.getextrema()
    response = HttpResponse(content_type="image/png")
    image.save(response, "PNG")
    return response

def proxy_tms(request, origin=None, slug=None, z=None, x=None, y=None, u=None, ext=None):

    #starttime = time.clock()
    # Check Existing Tile Sourcesi
    match_tilesource = None
    tilesources = getTileSources(proxy=True)
    for tilesource in tilesources:
        if tilesource.name == slug:
            match_tilesource = tilesource
            break

    if match_tilesource:
        if match_tilesource.origin.name != origin:
            print "Origin is not correct.  Tilesource is unique, but origin need to match too."
            print origin
            print tilesource.origin.name
            return None
        else:
            tile = requestTile(request,tileservice=None,tilesource=tilesource,z=z,x=x,y=y,u=u,ext=ext)
            #print "Time Elapsed: "+str(time.clock()-starttime)
            return tile


    # Check Existing Tile Origins to see if we need to create a new tile source
    match_tileorigin = None
    if origin:
        tileorigins = getTileOrigins(proxy=True)
        for tileorigin in tileorigins:
            if tileorigin.name == origin:
                match_tileorigin = tileorigin
                break

    if match_tileorigin:
        to = match_tileorigin
        if to.multiple:
            ts_url = to.url.replace('{slug}', slug)
            if TileSource.objects.filter(url=ts_url).count() > 0:
                print "Error: This souldn't happen.  You should have matched the tilesource earlier so you don't duplicate"
                return None
            exts = string_to_list(to.extensions)
            ts_pattern = url_to_pattern(ts_url, extensions=exts)
            ts = TileSource(auto=True,url=ts_url,pattern=ts_pattern,name=slug,type=to.type,extensions=exts,origin=to)
            ts.save()
            reloadTileSources(proxy=False)
            reloadTileSources(proxy=True)
            return requestTile(request,tileservice=None,tilesource=tilesource,z=z,x=x,y=y,u=u,ext=ext)
        else:
            ts = TileSource(auto=True,url=to.url,pattern=to.pattern,name=to.name,type=to.type,extensions=to.extensions)
            ts.save()
            reloadTileSources(proxy=False)
            reloadTileSources(proxy=True)
            return requestTile(request,tileservice=None,tilesource=tilesource,z=z,x=x,y=y,u=u,ext=ext)
    else:
        return None

