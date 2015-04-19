from django import forms
from django.utils.translation import ugettext as _
from django.conf import settings

#from modeltranslation.forms import TranslationModelForm

from .models import TileService
from ittc.source.models import TileOrigin, TileSource

from ittc.utils import service_to_url, url_to_pattern, IMAGE_EXTENSION_CHOICES

class TileOriginForm(forms.ModelForm):

    #name = forms.CharField(max_length=100)
    #description = forms.CharField(max_length=400, help_text=_('Human-readable description of the services provided by this tile origin.'))
    #url = forms.CharField(max_length=400, help_text=_('Used to generate url for new tilesource.'))
    #type = models.IntegerField(choices=TYPE_CHOICES, default=TYPE_TMS)

    extensions = forms.MultipleChoiceField(required=False,widget=forms.CheckboxSelectMultiple, choices=IMAGE_EXTENSION_CHOICES, help_text = _("Select which extensions are accepted for the {ext} parameter in the url.  If none are selected, then all that the source supports are allowed."))

    def __init__(self, *args, **kwargs):
        super(TileOriginForm, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        if self.cleaned_data['extensions']:
            extensions = self.cleaned_data['extensions']
            self.instance.pattern = url_to_pattern(self.cleaned_data['url'], extensions=extensions)
        else:
            self.instance.pattern = url_to_pattern(self.cleaned_data['url'])
        return super(TileOriginForm, self).save(*args, **kwargs)

    def clean(self):
        cleaned_data = super(TileOriginForm, self).clean()

        return cleaned_data

    class Meta():
        model = TileOrigin
        exclude = (
        #    'content_type',
        #    'object_id',
        #    'doc_file',
        #    'extension',
        #    'doc_type',
            'pattern',)

class TileSourceForm(forms.ModelForm):

    #name = forms.CharField(max_length=100)
    #description = forms.CharField(max_length=400, help_text=_('Human-readable description of the services provided by this tile origin.'))
    #url = forms.CharField(max_length=400, help_text=_('Used to generate url for new tilesource.'))
    #type = models.IntegerField(choices=TYPE_CHOICES, default=TYPE_TMS)

    extensions = forms.MultipleChoiceField(required=False,widget=forms.CheckboxSelectMultiple, choices=IMAGE_EXTENSION_CHOICES, help_text = _("Select which extensions are accepted for the {ext} parameter in the url.  If none are selected, then the proxy selects any of those listed."))

    def __init__(self, *args, **kwargs):
        super(TileSourceForm, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        if self.cleaned_data['extensions']:
            extensions = self.cleaned_data['extensions']
            self.instance.pattern = url_to_pattern(self.cleaned_data['url'],extensions=extensions)
        else:
            self.instance.pattern = url_to_pattern(self.cleaned_data['url'])
        return super(TileSourceForm, self).save(*args, **kwargs)

    def clean(self):
        cleaned_data = super(TileSourceForm, self).clean()
        return cleaned_data

    class Meta():
        model = TileSource
        exclude = (
        #    'content_type',
        #    'object_id',
        #    'doc_file',
        #    'extension',
        #    'doc_type',
            'pattern',)


class TileServiceForm(forms.ModelForm):


    extensions = forms.MultipleChoiceField(required=False,widget=forms.CheckboxSelectMultiple, choices=IMAGE_EXTENSION_CHOICES, help_text = _("Select which extensions are accepted for the {ext} parameter in the url.  If none are selected, then all that the source supports are allowed."))

    def __init__(self, *args, **kwargs):
        super(TileServiceForm, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        if self.cleaned_data['extensions']:
            name = self.cleaned_data['name']
            extensions = self.cleaned_data['extensions']
            self.instance.url = service_to_url(base=settings.SITEURL,name=name,extensions=extensions)
        else:
            self.instance.url = service_to_url(base=settings.SITEURL,name=name)
        return super(TileServiceForm, self).save(*args, **kwargs)

    def clean(self):
        cleaned_data = super(TileServiceForm, self).clean()
        return cleaned_data

    class Meta():
        model = TileService
        exclude = (
            'url',)

