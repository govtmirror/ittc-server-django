import json, os, datetime

from httplib import HTTPConnection, HTTPSConnection
from urlparse import urlsplit
from django.utils.http import is_safe_url
from django.http.request import validate_host

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
from ittc.utils import bbox_intersects, bbox_intersects_source, webmercator_bbox, flip_y, bing_to_tms, tms_to_bing, tms_to_bbox, getYValues, TYPE_TMS, TYPE_TMS_FLIPPED, TYPE_BING, TYPE_WMS, getRegexValue
from ittc.source.models import Origin, OriginPattern, TileSource
from ittc.cache.views import requestTile

def proxy(request):
    PROXY_ALLOWED_HOSTS = getattr(settings, 'PROXY_ALLOWED_HOSTS', ())

    host = None

    #if 'geonode.geoserver' in settings.INSTALLED_APPS:
    #    from geonode.geoserver.helpers import ogc_server_settings
    #    hostname = (ogc_server_settings.hostname,) if ogc_server_settings else ()
    #    PROXY_ALLOWED_HOSTS += hostname
    #    host = ogc_server_settings.netloc

    if 'url' not in request.GET:
        return HttpResponse("The proxy service requires a URL-encoded URL as a parameter.",
                            status=400,
                            content_type="text/plain"
                            )

    raw_url = request.GET['url']
    url = urlsplit(raw_url)
    locator = url.path
    if url.query != "":
        locator += '?' + url.query
    if url.fragment != "":
        locator += '#' + url.fragment

    if not settings.DEBUG:
        if not validate_host(url.hostname, PROXY_ALLOWED_HOSTS):
            return HttpResponse("DEBUG is set to False but the host of the path provided to the proxy service"
                                " is not in the PROXY_ALLOWED_HOSTS setting.",
                                status=403,
                                content_type="text/plain"
                                )
    headers = {}

    if settings.SESSION_COOKIE_NAME in request.COOKIES and is_safe_url(url=raw_url, host=host):
        headers["Cookie"] = request.META["HTTP_COOKIE"]

    if request.method in ("POST", "PUT") and "CONTENT_TYPE" in request.META:
        headers["Content-Type"] = request.META["CONTENT_TYPE"]

    print "Raw URL: "+ raw_url
    match_regex = None
    match_tilesource = None
    tilesources = TileSource.objects.exclude(pattern__isnull=True).exclude(pattern__exact='')
    for tilesource in tilesources:
        match = tilesource.match(raw_url)
        if match:
            match_regex = match
            match_tilesource = tilesource
            break

    if match_tilesource and match_regex:
        return proxy_tilesource(request, match_tilesource, match_regex)
    else:
        return None

    #origins = Origin.objects.all()
    #for origin in origins:
    #    match = origin.match(raw_url)
    #return None 


    #if url.scheme == 'https':
    #    conn = HTTPSConnection(url.hostname, url.port)
    #else:
    #    conn = HTTPConnection(url.hostname, url.port)
    #conn.request(request.method, locator, request.body, headers)

    #result = conn.getresponse()

    # If we get a redirect, let's add a useful message.
    #if result.status in (301, 302, 303, 307):
    #    response = HttpResponse(('This proxy does not support redirects. The server in "%s" '
    #                             'asked for a redirect to "%s"' % (url, result.getheader('Location'))),
    #                            status=result.status,
    #                            content_type=result.getheader("Content-Type", "text/plain")
    #                            )
    #
    #    response['Location'] = result.getheader('Location')
    #else:
    #    response = HttpResponse(
    #        result.read(),
    #        status=result.status,
    #        content_type=result.getheader("Content-Type", "text/plain"))
    #
    #return response

def proxy_tilesource(request, tilesource, match):
    if tilesource:
        z, x, y, u, ext = None, None, None, None, None
        z = getRegexValue(match, 'z')
        x = getRegexValue(match, 'x')
        y = getRegexValue(match, 'y')
        u = getRegexValue(match, 'u')
        ext = getRegexValue(match, 'ext') 
        return requestTile(request,tileservice=None,tilesource=tilesource,z=z,x=x,y=y,u=u,ext=ext)
    else:
        return HttpResponse(RequestContext(request, {}), status=404)

#def requestTile(request, tileservice=None, tilesource=None, z=None, x=None, y=None, u=None, ext=None):
