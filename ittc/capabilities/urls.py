from django.contrib.auth.decorators import login_required
from django.conf.urls import patterns, include, url

js_info_dict = {
    'packages': ('ittc.capabilities',),
}

urlpatterns = patterns('ittc.capabilities.views',
    url(r'^$', 'capabilities_all_xml', name='capabilities_all_xml'),
    url(r'^index\.html$', 'index', name='index'),
    url(r'^(?P<type>(all|regular|flipped))\.(?P<extension>(xml|html))$', 'capabilities', name='capabilities'),

    url(r'^service/(?P<slug>[^/]+)/?$', 'capabilities_service', name='capabilities_service'),

    url(r'^collection/(?P<slug>[^/]+)/export.gpx$', 'gpx_collection', name='gpx_collection'),
    url(r'^collection/(?P<slug>[^/]+)/?$', 'capabilities_collection', name='capabilities_collection_all'),
    url(r'^collection/(?P<slug>[^/]+)/(?P<type>(all|regular|flipped))\.(?P<extension>(html))$', 'capabilities_collection_html', name='capabilities_collection_html'),
    url(r'^collection/(?P<slug>[^/]+)/(?P<type>(all|regular|flipped))/$', 'capabilities_collection_doc', name='capabilities_collection_doc'),
    url(r'^collection/(?P<slug>[^/]+)/(?P<type>(all|regular|flipped))/(?P<extension>(xml))/(?P<docType>(tms|wms))/$', 'capabilities_collection_doc', name='capabilities_collection_doc'),

    url(r'^layer/(?P<slug>[^/]+)/export.gpx$', 'gpx_layer', name='gpx_layer'),
    url(r'^layer/(?P<slug>[^/]+)/?$', 'capabilities_layer', name='capabilities_layer_all'),
    url(r'^layer/(?P<slug>[^/]+)/(?P<type>(all|regular|flipped))\.(?P<extension>(xml|html))$', 'capabilities_layer', name='capabilities_layer'),

    #url(r'^collection/(?P<slug>[^/]+)/regular\.xml$', 'capabilities_collection_regular', name='capabilities_collection_regular'),
    #url(r'^collection/(?P<slug>[^/]+)/flipped\.xml$', 'capabilities_collection_flipped', name='capabilities_collection_flipped'),
)
