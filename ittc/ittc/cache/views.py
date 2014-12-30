import json, os, datetime

from django.shortcuts import render_to_response, get_object_or_404,render
from django.template.loader import render_to_string
from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext, loader
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.conf import settings
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.core.cache import caches, get_cache

import StringIO
from PIL import Image, ImageEnhance

from ittc.capabilities.models import TileService
from ittc.utils import webmercator_bbox, flip_y
from ittc.source.models import TileSource
#from ittc.cache.models import Tile

TYPE_TMS = 1
TYPE_TMS_FLIPPED = 2
TYPE_BING = 3
TYPE_WMS = 4

def render(request, template='capabilities/services.html', ctx=None, contentType=None):
    if not (contentType is None):
        return render_to_response(template, RequestContext(request, ctx), content_type=contentType)
    else:
        return render_to_response(template, RequestContext(request, ctx))

def capabilities_all_xml(request, template='capabilities/capabilities_1_0_0.xml'):
    return capabilities_all(request,template,'xml')

def capabilities_all(request, template=None, extension=None):
    ctx = {'tileservices': TileService.objects.all(),'title':'All Tile Services', 'SITEURL': settings.SITEURL,}
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

def tile_tms(request, slug=None, z=None, x=None, y=None, ext=None):

    ix = int(x)
    iy = int(y)
    iz = int(z)

    tilecache = caches['tiles']
    tileservice = get_object_or_404(TileService, slug=slug)
    tilesource = tileservice.tileSource

    if tileservice.serviceType == TYPE_TMS_FLIPPED:
        iy = flip_y(ix,iy,iz,256,webmercator_bbox)

    tile = None
    if z>= settings.ITTC_SERVER['cache']['memory']['minZoom'] and z <= settings.ITTC_SERVER['cache']['memory']['maxZoom']:
        key = "{layer},{z},{x},{y},{ext}".format(layer=tilesource.name,x=ix,y=iy,z=iz,ext=ext)
        tile = tilecache.get(key)
        if tile:
            image = Image.open(StringIO.StringIO(tile))
        else:
            tile = tilesource.requestTile(ix,iy,iz,ext,True)
            tilecache.set(key, tile)

    else:
        tile = tilesource.requestTile(ix,iy,iz,ext,True)

    image = Image.open(StringIO.StringIO(tile))        
    response = HttpResponse(content_type="image/png")
    image.save(response, "PNG")
    return response

