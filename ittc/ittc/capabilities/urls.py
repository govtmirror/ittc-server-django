from django.contrib.auth.decorators import login_required
from django.conf.urls import patterns, include, url

js_info_dict = {
    'packages': ('ittc.capabilities',),
}

urlpatterns = patterns('ittc.capabilities.views',
    url(r'^$', 'capabilities_all', name='capabilities_all'),

    url(r'^all\.xml?$', 'capabilities_all', name='capabilities_all'),
    url(r'^regular\.xml?$', 'capabilities_regular', name='capabilities_regular'),
    url(r'^flipped\.xml?$', 'capabilities_flipped', name='capabilities_flipped'),

    url(r'^service/(?P<slug>[^/]+)/?$', 'capabilities_service', name='capabilities_service'),

    url(r'^collection/(?P<slug>[^/]+)/?$', 'capabilities_collection_all', name='capabilities_collection_all'),
    url(r'^collection/(?P<slug>[^/]+)/all\.xml?$', 'capabilities_collection_all', name='capabilities_collection_all'),
    url(r'^collection/(?P<slug>[^/]+)/regular\.xml?$', 'capabilities_collection_regular', name='capabilities_collection_regular'),
    url(r'^collection/(?P<slug>[^/]+)/flipped\.xml?$', 'capabilities_collection_flipped', name='capabilities_collection_flipped'),
)
