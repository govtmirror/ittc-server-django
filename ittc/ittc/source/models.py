import datetime
import logging
import os
import io
import sys
import uuid
from base64 import b64encode
from optparse import make_option
import json
import urllib
import urllib2
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

from ittc.utils import bbox_intersects, bbox_intersects_source, webmercator_bbox, flip_y, bing_to_tms, tms_to_bing, tms_to_bbox, getYValues, TYPE_TMS, TYPE_TMS_FLIPPED, TYPE_BING, TYPE_WMS, TYPE_CHOICES

def make_request(url, params, auth=None, data=None, contentType=None):
    """
    Prepares a request from a url, params, and optionally authentication.
    """
    if params:
        url = url + urllib.urlencode(params)

    req = urllib2.Request(url, data=data)

    if auth:
        req.add_header('AUTHORIZATION', 'Basic ' + auth)

    if contentType:
        req.add_header('Content-type', contentType)
    else:
        if data:
            req.add_header('Content-type', 'text/xml')

    return urllib2.urlopen(req)

def parse_url(url):

    if (url is None) or len(url) == 0:
        return None

    index = url.rfind('/')

    if index != (len(url)-1):
        url += '/'

    return url

class Origin(models.Model):

    TYPE_CHOICES = [
        (TYPE_TMS, _("TMS")),
        (TYPE_TMS_FLIPPED, _("TMS - Flipped")),
        (TYPE_BING, _("Bing")),
        (TYPE_WMS, _("WMS"))
    ]

    name = models.CharField(max_length=100)
    description = models.CharField(max_length=400, help_text=_('Human-readable description of the services provided by this tile origin.'))
    type = models.IntegerField(choices=TYPE_CHOICES, default=TYPE_TMS)
    url = models.CharField(max_length=400, help_text=_('Used to generate url for new tilesource.'))

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ("name","type")
        verbose_name_plural = _("Origins")


    def type_title(self):
        return unicode([v for i, v in enumerate(TYPE_CHOICES) if v[0] == self.type][0][1]);


    def match(self, url):
        match = None
        patterns = OriginPattern.objects.filter(origin__pk=self.pk)
        for pattern in patterns:
            match = pattern.match(url)
            if match:
                break
        return match

class OriginPattern(models.Model):

    origin = models.ForeignKey(Origin,null=True,blank=True,help_text=_('The origin.'))
    includes = models.CharField(max_length=400,null=True,blank=True)
    excludes = models.CharField(max_length=400,null=True,blank=True)

    def __unicode__(self):
        return self.origin.name + " - "+str(self.pk)

    class Meta:
        ordering = ("origin", "includes", "excludes")
        verbose_name_plural = _("Origin Patterns")

    def match(self,url):
        print "matching includes: "+str(self.includes)
        print "matching excludes: "+str(self.excludes)
        print "matching url: "+str(url)
        match = None
        if self.includes:
            match = re.match(self.includes, url, re.M|re.I)
        if self.excludes:
            if re.match(self.excludes, url, re.M|re.I):
                match = None
        print "match: "+str(match)
        return match


class TileSource(models.Model):

    #TYPE_CHOICES = [
    #    (TYPE_TMS, _("TMS")),
    #    (TYPE_TMS_FLIPPED, _("TMS - Flipped")),
    #    (TYPE_BING, _("Bing")),
    #    (TYPE_WMS, _("WMS"))
    #]

    name = models.CharField(max_length=100)
    type = models.IntegerField(choices=TYPE_CHOICES, default=TYPE_TMS)
    auto = models.CharField(max_length=5, default="true")
    origin = models.ForeignKey(Origin,null=True,blank=True,help_text=_('The origin, if there is one.'))
    pattern = models.CharField(max_length=400,null=True,blank=True)
    url = models.CharField(max_length=100)
    extents = models.CharField(max_length=100,blank=True,null=True)
    minZoom = models.IntegerField(default=0,null=True,blank=True)
    maxZoom = models.IntegerField(default=None,null=True,blank=True)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ("name",)
        verbose_name_plural = _("Tile Sources")


    def type_title(self):
        return unicode([v for i, v in enumerate(TYPE_CHOICES) if v[0] == self.type][0][1]);


    def match(self, url):
        match = None
        if self.pattern:
            match = re.match(self.pattern, url, re.M|re.I)
        return match

    def requestTile(self,x,y,z,ext,verbose):
        url = self.url.format(x=x,y=y,z=z,ext=ext)
        contentType = "image/png"
        
        if verbose:
            print "Requesting tile from "+url

        request = make_request(url=url, params=None, auth=None, data=None, contentType=contentType)
        
        if request.getcode() != 200:
            raise Exception("Could not fetch tile from source with url {url}: Status Code {status}".format(url=url,status=request.getcode()))

        #image = binascii.hexlify(request.read())
        #image = io.BytesIO(request.read()))
        image = request.read()
        headers = request.info()

        tile = {
            'headers': headers,
            'data': image
        }
        return tile

