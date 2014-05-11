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

def capabilities(request, template='capabilities/capabilities_1_0_0.xml', ctx=None):
    return render_to_response(template, RequestContext(request, ctx), content_type='text/xml')

def capabilities_all(request, template='capabilities/capabilities_1_0_0.xml'):
    ctx = {'tileservices': TileService.objects.all(),}
    return capabilities(request,template,ctx)

def capabilities_regular(request, template='capabilities/capabilities_1_0_0.xml'):
    ctx = {'tileservices': TileService.objects.filter(serviceType__identifier='tms'),}
    return capabilities(request,template,ctx)

def capabilities_flipped(request, template='capabilities/capabilities_1_0_0.xml'):
    ctx = {'tileservices': TileService.objects.filter(serviceType__identifier='tms_flipped'),}
    return capabilities(request,template,ctx)

def capabilities_service(request, template='capabilities/capabilities_service_1_0_0.xml', slug=None):
    ctx = {'tileservice': TileService.objects.get(slug=slug),}
    return capabilities(request,template,ctx)

def capabilities_collection_all(request, template='capabilities/capabilities_1_0_0.xml', slug=None):
    layers = ([member.layer for member in CollectionMember.objects.filter(collection__slug=slug)])
    ctx = {'tileservices': TileService.objects.filter(layer__in=layers,)}
    return capabilities(request,template,ctx)

def capabilities_collection_regular(request, template='capabilities/capabilities_1_0_0.xml', slug=None):
    layers = [member.layer for member in CollectionMember.objects.filter(collection__slug=slug)]
    ctx = {'tileservices': TileService.objects.filter(layer__in=layers,serviceType__identifier='tms'),}
    return capabilities(request,template,ctx)

def capabilities_collection_flipped(request, template='capabilities/capabilities_1_0_0.xml', slug=None):
    layers = [member.layer for member in CollectionMember.objects.filter(collection__slug=slug)]
    ctx = {'tileservices': TileService.objects.filter(layer__in=layers,serviceType__identifier='tms_flipped'),}
    return capabilities(request,template,ctx)
