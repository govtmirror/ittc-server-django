from django.conf import settings
from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'ittc.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),
)

if 'ittc.capabilities' in settings.INSTALLED_APPS:
    urlpatterns += patterns('',
        (r'^capabilities/', include('ittc.capabilities.urls')),
    )

if 'ittc.cache' in settings.INSTALLED_APPS:
    urlpatterns += patterns('',
        (r'^cache/', include('ittc.cache.urls')),
    )
