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


from django.db import models
from django.db.models import signals
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse

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

class TileSource(models.Model):

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
    type = models.IntegerField(choices=TYPE_CHOICES, default=TYPE_TMS)
    url = models.CharField(max_length=100)
    extents = models.CharField(max_length=100,blank=True,null=True)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ("name",)
        verbose_name_plural = _("Source")

    def requestTile(self,x,y,z,ext,verbose):
        print "requesting tile"
        print "url base: "+self.url
        url = self.url.format(x=x,y=y,z=z,ext=ext)
        contentType = "image/png"
        
        if verbose:
            print "URL: "+url

        request = make_request(url=url, params=None, auth=None, data=None, contentType=contentType)
        
        if request.getcode() != 200:
            raise Exception("Could not fetch tile from source with url {url}: Status Code {status}".format(url=url,status=request.getcode()))

        #image = binascii.hexlify(request.read())
        #image = io.BytesIO(request.read()))
        image = request.read()
        return image

