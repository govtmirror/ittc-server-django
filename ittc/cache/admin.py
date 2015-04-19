from django.contrib import admin
from django.conf import settings

from .models import TileService

class TileServiceAdmin(admin.ModelAdmin):
    model = TileService
    list_display_links = ('id',)
    list_display = ('id', 'name', 'type', 'url')
    #list_editable = ('contact', 'resource', 'role')

admin.site.register(TileService, TileServiceAdmin)
