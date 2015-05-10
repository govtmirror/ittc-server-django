import datetime
import logging
import os
import io
import sys
import uuid
from base64 import b64encode
from optparse import make_option
import json
import argparse
import time
import os
import subprocess
import binascii
import re

from django.db import models
from django.db.models import signals
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse

from ittc.utils import getYValues, TYPE_TMS, TYPE_TMS_FLIPPED, TYPE_BING, TYPE_WMS, TYPE_CHOICES, IMAGE_EXTENSION_CHOICES, getValue


def parse_url(url):

    if (url is None) or len(url) == 0:
        return None

    index = url.rfind('/')

    if index != (len(url)-1):
        url += '/'

    return url

class TileOrigin(models.Model):

    TYPE_CHOICES = [
        (TYPE_TMS, _("TMS")),
        (TYPE_TMS_FLIPPED, _("TMS - Flipped")),
        (TYPE_BING, _("Bing")),
        (TYPE_WMS, _("WMS"))
    ]

    name = models.CharField(max_length=100)
    description = models.CharField(max_length=400, help_text=_('Human-readable description of the services provided by this tile origin.'))
    type = models.IntegerField(choices=TYPE_CHOICES, default=TYPE_TMS)
    cacheable = models.BooleanField(default=True, help_text=_('If true, tiles from the origin might be cached given other constraints.  If false, tiles from the origin will never be cached.'))
    multiple = models.BooleanField(default=True, help_text=_('If true, make sure to include {slug} in the url to be replaced by each source.'))
    auto = models.BooleanField(default=True, help_text=_('Should the proxy automatically create tile sources for this origin?'))
    url = models.CharField(max_length=400, help_text=_('Used to generate url for new tilesource.  For example, http://c.tile.openstreetmap.org/{z}/{x}/{y}.png.'))
    extensions = models.CharField(max_length=400,null=True,blank=True)
    pattern = models.CharField(max_length=400,null=True,blank=True)
    auth = models.CharField(max_length=400, blank=True, null=True, help_text=_('Authentication or access token.  Dynamically replaced in downstream sources by replacing {auth}.'))

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ("name","type")
        verbose_name_plural = _("Tile Origins")


    def type_title(self):
        return unicode([v for i, v in enumerate(TYPE_CHOICES) if v[0] == self.type][0][1]);


    #def match(self, url):
    #    match = None

    #    # If matches primary pattern, then check secondary patterns/filters.
    #    if self.pattern:
    #        match = re.match(self.pattern, url, re.M|re.I)

            #patterns = TileOriginPattern.objects.filter(origin__pk=self.pk)
            #for pattern in patterns:
            #    match = pattern.match(url)
            #    if match:
            #        break

        return match

class TileOriginPattern(models.Model):

    origin = models.ForeignKey(TileOrigin,null=True,blank=True,help_text=_('The origin.'))
    includes = models.CharField(max_length=400,null=True,blank=True)
    excludes = models.CharField(max_length=400,null=True,blank=True)

    def __unicode__(self):
        return self.origin.name + " - "+str(self.pk)

    class Meta:
        ordering = ("origin", "includes", "excludes")
        verbose_name_plural = _("Tile Origin Patterns")

    def match(self,url):
        #print "matching includes: "+str(self.includes)
        #print "matching excludes: "+str(self.excludes)
        #print "matching url: "+str(url)
        match = None
        if self.includes:
            match = re.match(self.includes, url, re.M|re.I)
        if self.excludes:
            if re.match(self.excludes, url, re.M|re.I):
                match = None
        #print "match: "+str(match)
        return match


class TileSource(models.Model):

    name = models.CharField(max_length=100)
    description = models.CharField(max_length=400, null=True, blank=True, help_text=_('Human-readable description of this tile source.'))
    type = models.IntegerField(choices=TYPE_CHOICES, default=TYPE_TMS)
    auto = models.BooleanField(default=True, help_text=_('Was the tile source created automatically by the proxy or manually by a user?'))
    cacheable = models.BooleanField(default=True, help_text=_('If true, tiles from this source might be cached given other constraints.  If false, tiles from this source will never be cached.'))
    origin = models.ForeignKey(TileOrigin,null=True,blank=True,help_text=_('The Tile Origin, if there is one.'))
    url = models.CharField(max_length=400, help_text=_('Standard Tile URL.  If applicable, replace {slug} from origin.  For example, http://c.tile.openstreetmap.org/{z}/{x}/{y}.{ext}.  If url includes {auth}, it is dynamically replaced with the relevant auth token stored with origin.'))
    #extensions = models.CharField(max_length=400,null=True,blank=True,choices=IMAGE_EXTENSION_CHOICES)
    extensions = models.CharField(max_length=400,null=True,blank=True)
    pattern = models.CharField(max_length=400,null=True,blank=True)
    extents = models.CharField(max_length=800,blank=True,null=True)
    minZoom = models.IntegerField(default=0,null=True,blank=True)
    maxZoom = models.IntegerField(default=None,null=True,blank=True)
    
    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ("name",)
        verbose_name_plural = _("Tile Sources")

    @property
    def tileservices(self):
        return self.tileservice_set

    def type_title(self):
        return unicode([v for i, v in enumerate(TYPE_CHOICES) if v[0] == self.type][0][1]);
