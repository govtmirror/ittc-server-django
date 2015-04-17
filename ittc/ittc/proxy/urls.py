from django.contrib.auth.decorators import login_required
from django.conf.urls import patterns, include, url

js_info_dict = {
    'packages': ('ittc.proxy',),
}

urlpatterns = patterns('ittc.proxy.views',
    url(r'^proxy/', 'proxy')
    url(r'^proxy/tms/orign/(?P<origin>[^/]+)/source/(?P<slug>[^/]+)/(?P<z>[^/]+)/(?P<x>[^/]+)/(?P<y>[^/]+)\.(?P<ext>(png|gif|jpg|jpeg))$', 'proxy_tms', name='proxy_tms'),
    url(r'^proxy/bing/orign/(?P<origin>[^/]+)/source/(?P<slug>[^/]+)/(?P<u>[^/]+)\.(?P<ext>(png|gif|jpg|jpeg))$', 'proxy_tms', name='proxy_bing'),
)
