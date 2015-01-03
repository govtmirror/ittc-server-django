from django.contrib import admin
from django.conf import settings

from ittc.source.models import Origin, OriginPattern, TileSource

class OriginAdmin(admin.ModelAdmin):
    model = TileSource
    list_display_links = ('id',)
    list_display = ('id', 'name', 'type', 'url')

class OriginPatternAdmin(admin.ModelAdmin):
    model = TileSource
    list_display_links = ('id',)
    list_display = ('id', 'origin', 'includes', 'excludes')

class TileSourceAdmin(admin.ModelAdmin):
    model = TileSource
    list_display_links = ('id',)
    list_display = ('id', 'name', 'type', 'url')
    #list_editable = ('contact', 'resource', 'role')

admin.site.register(Origin, OriginAdmin)
admin.site.register(OriginPattern, OriginPatternAdmin)
admin.site.register(TileSource, TileSourceAdmin)
