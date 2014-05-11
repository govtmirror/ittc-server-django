import datetime
import logging
import os
import sys
import uuid

from django.db import models
from django.db.models import signals
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse

class Layer(models.Model):
    """
    A layer is an asbtraction above services.  For example, for one layer there can be a TMS, TMS-Flipped, etc. services.
    """
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ("name",)
        verbose_name_plural = _("Layers")

class Collection(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    slug = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name

    class meta:
        order = ("name",)
        verbose_name_pural = _("Collection")

class CollectionMember(models.Model):
    collection = models.ForeignKey(Collection,null=True,blank=True)
    layer = models.ForeignKey(Layer,null=True,blank=True)

    class meta:
        order = ("collection","layer__name")
        verbose_name_pural = _("Collection Members")

class ImageType(models.Model):
    identifier = models.CharField(max_length=255, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    mimeType = models.CharField(max_length=20)
    extension = models.CharField(max_length=5)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ("identifier",)
        verbose_name_plural = _("Image Types")

class TileServiceType(models.Model):
    identifier = models.CharField(max_length=255, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ("identifier",)
        verbose_name_plural = _("Tile Service Types")

class Server(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    url = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ("name",)
        verbose_name_plural = _("Servers")

class TileService(models.Model):
    """
    A tile service, such as TMS, TMS-Flipped, WMTS, Bing, etc.
    """
    name = models.CharField(max_length=100)
    layer = models.ForeignKey(Layer, help_text=_('The related layer'))
    serviceType = models.ForeignKey(TileServiceType, help_text=_('The type of tile service (e.g., TMS, TMS-Flipped, Bing, etc.).'))
    srs = models.CharField(max_length=20)
    url_capabilities = models.CharField(max_length=255, help_text=_('The url for the service capabilities document if remote.'))
    #=#
    server = models.ForeignKey(Server,null=True,blank=True,help_text=_('The server hosting the tile servie'))
    slug = models.CharField(max_length=100,null=True,blank=True)
    tileWidth = models.PositiveSmallIntegerField(help_text=_('The width of the tiles in pixels.'))
    tileHeight = models.PositiveSmallIntegerField(help_text=_('The width of the tiles in pixels.'))
    imageType = models.ForeignKey(ImageType, help_text=_('The type of image (e.g., png, jpeg, etc.).'))

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ("name","layer",)
        verbose_name_plural = _("Tile Services")

    @property
    def url(self):
        if (not (self.url_capabilities is None)) and (len(self.url_capabilities) > 0):
            return self.url_capabilities
        elif (not (self.server is None)) and (not (self.slug is None)) and (len(self.slug) > 0):
            return self.server.url+self.slug+"/"



