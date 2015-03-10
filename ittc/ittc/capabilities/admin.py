from django.contrib import admin
#from ittc.capabilities.models import Server, Extent, Layer, Collection, CollectionMember, TileService, TileServiceType, ImageType
from ittc.capabilities.models import Server, Extent, Layer, Collection, CollectionMember, TileServiceType, ImageType

class ExtentAdmin(admin.ModelAdmin):
    model = Layer
    list_display_links = ('id',)
    list_display = ('id','bbox')

class LayerAdmin(admin.ModelAdmin):
    model = Layer
    list_display_links = ('id','name',)
    list_display = ('id','name','slug',)

class CollectionAdmin(admin.ModelAdmin):
    model = Collection
    list_display_links = ('id','name',)
    list_display = ('id','name','slug',)

class CollectionMemberAdmin(admin.ModelAdmin):
    model = CollectionMember
    list_display_links = ('id',)
    list_display = ('id','collection','layer',)

#class TileServiceAdmin(admin.ModelAdmin):
#    model = Layer
#    list_display_links = ('id','name',)
#    list_display = ('id','name','serviceType','imageType')

#class TileServiceAdmin(admin.ModelAdmin):
#    model = Layer
#    list_display_links = ('id','name',)
#    list_display = ('id','name','slug','serviceType','srs')


class TileServiceTypeAdmin(admin.ModelAdmin):
    model = Layer
    list_display_links = ('identifier',)
    list_display = ('identifier','name','description')

class ImageTypeAdmin(admin.ModelAdmin):
    model = Layer
    list_display_links = ('identifier',)
    list_display = ('identifier','name','description')

class ServerAdmin(admin.ModelAdmin):
    model = Server
    list_display_links = ('id','name',)
    list_display = ('id','name',)

admin.site.register(Layer, LayerAdmin)
admin.site.register(Collection,CollectionAdmin)
admin.site.register(CollectionMember,CollectionMemberAdmin)
#admin.site.register(TileService, TileServiceAdmin)
admin.site.register(TileServiceType, TileServiceTypeAdmin)
admin.site.register(ImageType, ImageTypeAdmin)
admin.site.register(Server, ServerAdmin)
admin.site.register(Extent, ExtentAdmin)
