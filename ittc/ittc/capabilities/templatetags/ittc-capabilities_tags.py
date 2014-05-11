from django import template

from django.db.models import Count
from django.contrib.contenttypes.models import ContentType

from ittc.capabilities.models import Layer, TileService, TileServiceType

register = template.Library()

@register.assignment_tag
def layers():
    layers = Layer.objects.all()
    return layers

@register.assignment_tag
def tileservices():
    tileservices = TileService.objects.all()
    return tileservices
