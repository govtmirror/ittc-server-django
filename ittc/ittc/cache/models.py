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

from ittc.source.models import TileSource

from ittc.utils import bbox_intersects, bbox_intersects_source, webmercator_bbox, flip_y, bing_to_tms, tms_to_bing, tms_to_bbox, getYValues, TYPE_TMS, TYPE_TMS_FLIPPED, TYPE_BING, TYPE_WMS, TYPE_CHOICES, IMAGE_EXTENSION_CHOICES


class TileService(models.Model):
    """
    A tile service, such as TMS, TMS-Flipped, WMTS, Bing, etc.
    """

    name = models.CharField(max_length=100)
    description = models.CharField(max_length=400, null=True, blank=True, help_text=_('Human-readable description of the services provided by this tile origin.'))
    type = models.IntegerField(choices=TYPE_CHOICES, default=TYPE_TMS)
    source = models.ForeignKey(TileSource,null=True,blank=True,help_text=_('The source of the tiles.'), related_name='tileservice_set')
    extensions = models.CharField(max_length=400,null=True,blank=True)
    url = models.CharField(max_length=400,null=True,blank=True)
    #slug = models.CharField(max_length=100,null=True,blank=True)
    #srs = models.CharField(max_length=20)
    #=#
    #tileSource = models.ForeignKey(TileSource,null=True,blank=True,help_text=_('The source of the tiles.'))
    #tileWidth = models.PositiveSmallIntegerField(help_text=_('The width of the tiles in pixels.'))
    #tileHeight = models.PositiveSmallIntegerField(help_text=_('The width of the tiles in pixels.'))

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ("name","type",)
        verbose_name_plural = _("Tile Services")

    def type_title(self):
        return unicode([v for i, v in enumerate(TYPE_CHOICES) if v[0] == self.type][0][1]);

    @property
    def url_capabilities(self):
        return settings.SITEURL+"cache/tms/"+self.name

