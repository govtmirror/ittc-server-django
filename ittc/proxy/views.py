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
from django.core.cache import cache, caches, get_cache

import StringIO
from PIL import Image, ImageEnhance

from ittc.cache.models import TileService
from ittc.utils import getYValues, TYPE_TMS, TYPE_TMS_FLIPPED, TYPE_BING, TYPE_WMS, getRegexValue, url_to_pattern, string_to_list
from ittc.source.models import TileOrigin, TileOriginPattern, TileSource
from ittc.source.utils import getTileOrigins, reloadTileOrigins, getTileSources, reloadTileSources
from ittc.cache.views import _requestTile

from tilejetutil.tileregex import match_pattern_url

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

    # Try to match against existing tile sources
    #tilesources = TileSource.objects.exclude(pattern__isnull=True).exclude(pattern__exact='')
    tilesources = getTileSources(proxy=True)
    for tilesource in tilesources:
        match = match_pattern_url(tilesource.pattern, raw_url)
        if match:
            match_regex = match
            match_tilesource = tilesource
            break

    if match_tilesource and match_regex:
        return proxy_tilesource(request, match_tilesource, match_regex)
    #else:
    #    return HttpResponse('No matching tilesource found.',RequestContext(request, {}), status=404)

    # Try to match against existing origins that can automatically create tile sources (auto=true)
    match_tileorigin = None
    #tileorigins = TileOrigin.objects.exclude(pattern__isnull=True).exclude(pattern__exact='').filter(auto=True)
    tileorigins = getTileOrigins(proxy=True)
    for tileorigin in tileorigins:
        match = match_pattern_url(tileorigin.pattern, raw_url)
        if match:
            match_regex = match
            match_tileorigin = tileorigin
            break

    if match_tileorigin and match_regex:
        to = match_tileorigin
        if to.multiple:
            slug = getRegexValue(match_regex, 'slug')
            ts_url = to.url.replace('{slug}', slug)
            #print "ts_url: "+ts_url
            if TileSource.objects.filter(url=ts_url).count() > 0:
                print "Error: This souldn't happen.  You should have matched the tilesource earlier so you don't duplicate"
                return None
            exts = string_to_list(to.extensions)
            ts_pattern = url_to_pattern(ts_url, extensions=exts)
            ts = TileSource(auto=True,url=ts_url,pattern=ts_pattern,name=slug,type=to.type,extensions=exts,origin=to)
            ts.save()
            reloadTileSources(proxy=False)
            reloadTileSources(proxy=True)
            return proxy_tilesource(request, ts, match_regex)
        else:
            ts = TileSource(auto=True,url=to.url,pattern=to.pattern,name=to.name,type=to.type,extensions=to.extensions)
            ts.save()
            reloadTileSources(proxy=False)
            reloadTileSources(proxy=True)
            return proxy_tilesource(request, ts, match_regex)
    else:
        return HttpResponse('No matching tile origin or tile source found.',RequestContext(request, {}), status=404)


def proxy_tilesource(request, tilesource, match):
    if tilesource:
        z, x, y, u, ext = None, None, None, None, None
        z = getRegexValue(match, 'z')
        x = getRegexValue(match, 'x')
        y = getRegexValue(match, 'y')
        u = getRegexValue(match, 'u')
        ext = getRegexValue(match, 'ext')
        return _requestTile(request,tileservice=None,tilesource=tilesource,z=z,x=x,y=y,u=u,ext=ext)
    else:
        return HttpResponse(RequestContext(request, {}), status=404)


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


#def requestTile(request, tileservice=None, tilesource=None, z=None, x=None, y=None, u=None, ext=None):
