import json, os

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

from ittc.capabilities.models import Layer, Collection, CollectionMember, TileService, TileServiceType

def index(request, template='capabilities/index.html'):
    ctx = {'title':'Index','collections':Collection.objects.all(),'layers':Layer.objects.all(),'tileservices': TileService.objects.all()}
    return render_to_response(template, RequestContext(request, ctx))

def capabilities(request, template='capabilities/services.html', ctx=None, contentType=None):
    if not (contentType is None):
        return render_to_response(template, RequestContext(request, ctx), content_type=contentType)
    else:
        return render_to_response(template, RequestContext(request, ctx))

def capabilities_all_html(request, template='capabilities/services.html'):
    return capabilities_all(request,template,'html')

def capabilities_all_xml(request, template='capabilities/capabilities_1_0_0.xml'):
    return capabilities_all(request,template,'xml')

def capabilities_all(request, template=None, extension=None):
    ctx = {'tileservices': TileService.objects.all(),'title':'All Tile Services'}
    if extension=="xml":
        if template is None:
            template = 'capabilities/capabilities_1_0_0.xml'
        return capabilities(request,template,ctx,'text/xml')
    else:
        if template is None:
            template ='capabilities/services.html'
        return capabilities(request,template,ctx)

def capabilities_regular(request, template=None, extension=None):
    ctx = {'tileservices': TileService.objects.filter(serviceType__identifier='tms'),'title':'Regular Tile Services'}
    if extension=="xml":
        if template is None:
            template = 'capabilities/capabilities_1_0_0.xml'
        return capabilities(request,template,ctx,'text/xml')
    else:
        if template is None:
            template ='capabilities/services.html'
        return capabilities(request,template,ctx)

def capabilities_flipped(request, template=None, extension=None):
    ctx = {'tileservices': TileService.objects.filter(serviceType__identifier='tms_flipped'),'title':'Flipped Tile Services'}
    if extension=="xml":
        if template is None:
            template = 'capabilities/capabilities_1_0_0.xml'
        return capabilities(request,template,ctx,'text/xml')
    else:
        if template is None:
            template ='capabilities/services.html'
        return capabilities(request,template,ctx)

def capabilities_service(request, template='capabilities/capabilities_service_1_0_0.xml', slug=None):
    ctx = {'tileservice': TileService.objects.get(slug=slug),}
    return capabilities(request,template,ctx,'text/xml')

def capabilities_collection_all(request, template='capabilities/capabilities_1_0_0.xml', slug=None):
    layers = ([member.layer for member in CollectionMember.objects.filter(collection__slug=slug)])
    ctx = {'tileservices': TileService.objects.filter(layer__in=layers,)}
    return capabilities(request,template,ctx,'text/xml')

def capabilities_collection_all(request, template=None, slug=None, extension=None):
    collection = Collection.objects.get(slug=slug)
    layers = ([member.layer for member in CollectionMember.objects.filter(collection__slug=slug)])
    ctx = {'tileservices': TileService.objects.filter(layer__in=layers,),'title':'All Tile Services for Collection '+collection.name}
    if extension=="xml":
        if template is None:
            template = 'capabilities/capabilities_1_0_0.xml'
        return capabilities(request,template,ctx,'text/xml')
    else:
        if template is None:
            template ='capabilities/services.html'
        return capabilities(request,template,ctx)

def capabilities_collection_regular(request, template='capabilities/capabilities_1_0_0.xml', slug=None):
    layers = [member.layer for member in CollectionMember.objects.filter(collection__slug=slug)]
    ctx = {'tileservices': TileService.objects.filter(layer__in=layers,serviceType__identifier='tms'),}
    return capabilities(request,template,ctx,'text/xml')

def capabilities_collection_flipped(request, template='capabilities/capabilities_1_0_0.xml', slug=None):
    layers = [member.layer for member in CollectionMember.objects.filter(collection__slug=slug)]
    ctx = {'tileservices': TileService.objects.filter(layer__in=layers,serviceType__identifier='tms_flipped'),}
    return capabilities(request,template,ctx,'text/xml')
