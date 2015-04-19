from django.contrib import admin
from django.conf import settings

from ittc.source.models import TileOrigin, TileOriginPattern, TileSource

class TileOriginAdmin(admin.ModelAdmin):
    model = TileOrigin
    list_display_links = ('id',)
    list_display = ('id', 'name', 'type', 'url')

class TileOriginPatternAdmin(admin.ModelAdmin):
    model = TileSource
    list_display_links = ('id',)
    list_display = ('id', 'origin', 'includes', 'excludes')

class TileSourceAdmin(admin.ModelAdmin):
    model = TileSource
    list_display_links = ('id',)
    list_display = ('id', 'name', 'type', 'url')
    #list_editable = ('contact', 'resource', 'role')

admin.site.register(TileOrigin, TileOriginAdmin)
admin.site.register(TileOriginPattern, TileOriginPatternAdmin)
admin.site.register(TileSource, TileSourceAdmin)
