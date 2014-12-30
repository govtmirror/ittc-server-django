import datetime
import logging
import os
import sys
import uuid

from django.db import models
from django.db.models import signals
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse

from ..source.models import TileSource

class Point(models.Model):
    x = models.FloatField()
    y = models.FloatField()

    class Meta:
        ordering = ("x","y",)
        verbose_name_plural = _("x","y",)

class Segment:
    
    def __init__(self):
        self.points = []

    def add(self,point):
        self.points.append(point)

class Track:
    
    def __init__(self,name,segments=None):
        self.name = name
        self.segments = segments

class Link(models.Model):
    label = models.CharField(max_length=100)
    url = models.CharField(max_length=100)

    class Meta:
        ordering = ("label","url",)
        verbose_name_plural = _("Links")

class Extent(models.Model):
    left = models.FloatField(help_text=_('The left or minimum value along the X axis.'))
    bottom = models.FloatField(help_text=_('The bottom or minimum value along the Y axis.'))
    right = models.FloatField(help_text=_('The right or maximum value along the X axis')) 
    top = models.FloatField(help_text=_('The top or maximum value along the Y axis'))

    def init(self,extent):
        self.left = extent.left
        self.bottom = extent.bottom
        self.right = extent.right
        self.top = extent.top

    @property
    def valid(self):
        valid = True
        valid = valid and (not (self.left is None))
        valid = valid and (not (self.bottom is None))
        valid = valid and (not (self.right is None))
        valid = valid and (not (self.top is None))
        return valid

    def extend(self,extent):
        self.left = min(self.left,extent.left)
        self.bottom = min(self.bottom,extent.bottom)
        self.right = max(self.right,extent.right)
        self.top = max(self.top,extent.top) 

    @property
    def bottomLeft(self):
        if self.valid:
            return Point(x=self.left,y=self.bottom)
        else:
            return None

    @property
    def bottomRight(self):
        if self.valid:
            return Point(x=self.right,y=self.bottom)
        else:
            return None

    @property
    def topRight(self):
        if self.valid:
            return Point(x=self.right,y=self.top)
        else:
            return None

    @property
    def topLeft(self):
        if self.valid:
            return Point(x=self.left,y=self.top)
        else:
            return None

    @property
    def gpxSegment(self):
        if self.valid:
            seg = Segment()
            seg.add(self.bottomLeft)
            seg.add(self.bottomRight)
            seg.add(self.topRight)
            seg.add(self.topLeft)
            seg.add(self.bottomLeft)
            return seg
        else:
            return None

    @property
    def center(self):
        if self.valid:
            return Point(x=(self.left+self.right)/2.0,y=(self.bottom+self.top)/2.0)
        else:
            return None

    @property
    def bbox(self):
        coords = [];
        coords.append('%.2f' % self.left)
        coords.append('%.2f' % self.bottom)
        coords.append('%.2f' % self.right)
        coords.append('%.2f' % self.top)
        return ",".join(coords)

    @property
    def url_hiu(self):
        if self.valid:
            domain = "http://state-hiu.github.io"
            ctx = "cybergis-client-examples/1.0/osm/osm.html"
            qs = []
            c = self.center
            qs.append("z=8")
            qs.append("lat="+('%.2f' % c.y))
            qs.append("lon="+('%.2f' % c.x))
            qs.append("aoi_ll="+self.bbox)
            return domain+"/"+ctx+"?"+("&".join(qs))
        else:
            return None

    @property
    def link_hiu(self):
        if self.valid:
            return Link(label="HIU",url=self.url_hiu)
        else:
            return None

class Layer(models.Model):
    """
    A layer is an asbtraction above services.  For example, for one layer there can be a TMS, TMS-Flipped, etc. services.
    """
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    slug = models.CharField(max_length=100,null=True,blank=True)
    extent = models.ForeignKey(Extent,null=True,blank=True)
    source = models.ForeignKey(TileSource,null=True,blank=True)
    
    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ("name",)
        verbose_name_plural = _("Layers")

    @property
    def trk(self):
        trk = Track(name=self.name,segments=[self.extent.gpxSegment])
        return trk


class Collection(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    slug = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name

    class meta:
        order = ("name",)
        verbose_name_pural = _("Collection")

    @property
    def extent(self):
        layers = [member.layer for member in CollectionMember.objects.filter(collection__slug=self.slug)]
        if len(layers) > 0:
            extent = Extent()
            extent.init(layers[0].extent)
            for i in range(1,len(layers)):
                extent.extend(layers[i].extent)
            return extent
        else:
            return None

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

class TileServiceOld(models.Model):
    """
    A tile service, such as TMS, TMS-Flipped, WMTS, Bing, etc.
    """
    name = models.CharField(max_length=100)
    layer = models.ForeignKey(Layer, help_text=_('The related layer'))
    serviceType = models.ForeignKey(TileServiceType, help_text=_('The type of tile service (e.g., TMS, TMS-Flipped, Bing, etc.).'))
    srs = models.CharField(max_length=20)
    url_serverless = models.CharField(max_length=255, help_text=_('The url for the service capabilities document if remote.'))
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
    def url_base(self):
        if (not (self.url_serverless is None)) and (len(self.url_serverless) > 0):
            return self.url_serverless
        elif (not (self.server is None)) and (not (self.slug is None)) and (len(self.slug) > 0):
            return self.server.url+self.slug+"/"

    @property
    def url_id(self):
        if self.serviceType.identifier=="tms_flipped":
            domain = "https://www.openstreetmap.org"
            ctx = "edit"
            qs1 = []
            qs1.append("editor=id")
            qs2 = []
            c = self.layer.extent.center
            qs2.append("map=8/"+('%.4f' % c.y)+"/"+('%.4f' % c.x))
            qs2.append("gpx="+settings.SITEURL+"capabilities/layer/"+self.layer.slug+"/export.gpx")
            qs2.append("background=custom:"+self.url_base+"{z}/{x}/{y}."+self.imageType.extension)
            return domain+"/"+ctx+"?"+("&".join(qs1))+"#"+("&".join(qs2))
        else:
            return None

    @property
    def url_josm(self):
        if self.serviceType.identifier=="tms_flipped" or self.serviceType.identifier=="tms":
            domain = "http://127.0.0.1:8111"
            ctx = "imagery"
            qs = []
            qs.append("title="+self.layer.name)
            qs.append("type=tms")
            if self.serviceType.identifier=="tms_flipped":
                qs.append("url=tms[22]:"+self.url_base+"{zoom}/{x}/{y}."+self.imageType.extension)
            elif self.serviceType.identifier=="tms":
                qs.append("url=tms[22]:"+self.url_base+"{zoom}/{x}/{-y}."+self.imageType.extension)
            return domain+"/"+ctx+"?"+("&".join(qs))
        else:
            return None

    @property
    def url_hiu(self):
        if self.serviceType.identifier=="tms" or self.serviceType.identifier=="tms_flipped":
            domain = "http://state-hiu.github.io"
            ctx = "cybergis-client-examples/1.0/osm/osm.html"
            qs = []
            c = self.layer.extent.center
            qs.append("z=8")
            qs.append("lat="+('%.2f' % c.y))
            qs.append("lon="+('%.2f' % c.x))
            qs.append("aoi_ll="+self.layer.extent.bbox)
            return domain+"/"+ctx+"?"+("&".join(qs))
        else:
            return None

    @property
    def links(self):
        links = []
        if self.serviceType.identifier=="tms_flipped":
            links.append(Link(label="iD",url=self.url_id))
        if self.serviceType.identifier=="tms" or self.serviceType.identifier=="tms_flipped":
            links.append(Link(label="JOSM",url=self.url_josm))
        if self.serviceType.identifier=="tms" or self.serviceType.identifier=="tms_flipped":
            links.append(Link(label="HIU",url=self.url_hiu))
        return links

class TileService(models.Model):
    """
    A tile service, such as TMS, TMS-Flipped, WMTS, Bing, etc.
    """

    TYPE_TMS = 1
    TYPE_TMS_FLIPPED = 2
    TYPE_BING = 3
    TYPE_WMS = 4

    TYPE_CHOICES = [
        (TYPE_TMS, _("TMS")),
        (TYPE_TMS_FLIPPED, _("TMS - Flipped")),
        (TYPE_BING, _("Bing")),
        (TYPE_WMS, _("WMS"))
    ]

    name = models.CharField(max_length=100)
    slug = models.CharField(max_length=100,null=True,blank=True)
    description = models.TextField(null=True, blank=True)
    serviceType = models.IntegerField(choices=TYPE_CHOICES, default=TYPE_TMS)
    srs = models.CharField(max_length=20)
    #=#
    tileSource = models.ForeignKey(TileSource,null=True,blank=True,help_text=_('The source of the tiles.'))
    tileWidth = models.PositiveSmallIntegerField(help_text=_('The width of the tiles in pixels.'))
    tileHeight = models.PositiveSmallIntegerField(help_text=_('The width of the tiles in pixels.'))

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ("name","slug",)
        verbose_name_plural = _("Tile Services")

    @property
    def url_capabilities(self):
        return settings.SITEURL+"cache/tms/"+self.slug

