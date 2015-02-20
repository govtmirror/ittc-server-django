from django.contrib.auth.decorators import login_required
from django.conf.urls import patterns, include, url

js_info_dict = {
    'packages': ('ittc.cache',),
}

urlpatterns = patterns('ittc.cache.views',
    url(r'^flush$', 'flush', name='flush'),

    url(r'^sources$', 'sources_list', name='sources_list'),
    url(r'^sources/export/sources.json$', 'sources_json', name='sources_json'),

    url(r'^origins$', 'origins_list', name='origins_list'),
    url(r'^origins/export/origins.json$', 'origins_json', name='origins_json'),

    url(r'^logs/reload$', 'logs_reload', name='logs_reload'),
    url(r'^logs/clear$', 'logs_clear', name='logs_clear'),
    url(r'^logs/export/json$', 'logs_json', name='logs_json'),

    url(r'^stats/reload$', 'stats_reload', name='stats_reload'), 
    url(r'^stats/clear$', 'stats_clear', name='stats_clear'),
    url(r'^stats/export/json$', 'stats_json', name='stats_json'),
    url(r'^stats/export/tms/(?P<t>[^/]+)/(?P<stat>[^/]+)/(?P<z>[^/]+)/(?P<x>[^/]+)/(?P<y>[^/]+)\.(?P<ext>(png|gif|jpg|jpeg))$', 'stats_tms', name='stats_tms'),

    url(r'^stats/export/geojson/(?P<z>[^/]+)\.geojson$', 'stats_geojson', name='stats_geojson'),
    url(r'^stats/export/geojson/(?P<z>[^/]+)/origin/(?P<origin>[^/]+)\.geojson$', 'stats_geojson', name='stats_geojson_origin'),
    url(r'^stats/export/geojson/(?P<z>[^/]+)/source/(?P<source>[^/]+)\.geojson$', 'stats_geojson', name='stats_geojson_source'),
    url(r'^stats/export/geojson/(?P<z>[^/]+)/date/(?P<date>[^/]+)\.geojson$', 'stats_geojson', name='stats_geojson_date'),
    url(r'^stats/export/geojson/(?P<z>[^/]+)/source/(?P<source>[^/]+)/date/(?P<date>[^/]+)\.geojson$', 'stats_geojson', name='stats_geojson_source_date'),


    url(r'^stats/map$', 'stats_map', name='stats_map'),
    url(r'^stats/map/origin/(?P<origin>[^/]+)$', 'stats_map', name='stats_map_origin'),
    url(r'^stats/map/source/(?P<source>[^/]+)$', 'stats_map', name='stats_map_source'),
    url(r'^stats/map/date/(?P<date>[^/]+)$', 'stats_map', name='stats_map_date'),\
    url(r'^stats/map/source/(?P<source>[^/]+)/date/(?P<date>[^/]+)$', 'stats_map', name='stats_map_source_date'),

    url(r'^stats/dashboard$', 'stats_dashboard', name='stats_dashboard'),
    url(r'^stats/dashboard/origin/(?P<origin>[^/]+)$', 'stats_dashboard', name='stats_dashboard_origin'),
    url(r'^stats/dashboard/source/(?P<source>[^/]+)$', 'stats_dashboard', name='stats_dashboard_source'),
    url(r'^stats/dashboard/date/(?P<date>[^/]+)$', 'stats_dashboard', name='stats_dashboard_date'),
    
    url(r'^tms/$', 'capabilities_all_xml', name='capabilities_all_xml'),
    url(r'^tms/(?P<slug>[^/]+)/$', 'capabilities_service', name='capabilities_service'),
    url(r'^tms/(?P<slug>[^/]+)/(?P<z>[^/]+)/(?P<x>[^/]+)/(?P<y>[^/]+)\.(?P<ext>(png|gif|jpg|jpeg))$', 'tile_tms', name='tile_tms'),
    url(r'^bing/(?P<slug>[^/]+)/(?P<u>[^/]+)\.(?P<ext>(png|gif|jpg|jpeg))$', 'tile_tms', name='tile_bing')
)
