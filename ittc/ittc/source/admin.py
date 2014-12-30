from django.contrib import admin
from django.conf import settings

from ittc.source.models import TileSource

class TileSourceAdmin(admin.ModelAdmin):
    model = TileSource
    list_display_links = ('id',)
    list_display = ('id', 'name', 'type', 'url')
    #list_editable = ('contact', 'resource', 'role')

admin.site.register(TileSource, TileSourceAdmin)
