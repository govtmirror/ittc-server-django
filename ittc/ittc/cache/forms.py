from django import forms
from django.utils.translation import ugettext as _

#from modeltranslation.forms import TranslationModelForm

from ittc.source.models import TileOrigin, TileSource

from ittc.utils import url_to_pattern, IMAGE_EXTENSION_CHOICES

class TileOriginForm(forms.ModelForm):

    #name = forms.CharField(max_length=100)
    #description = forms.CharField(max_length=400, help_text=_('Human-readable description of the services provided by this tile origin.'))
    #url = forms.CharField(max_length=400, help_text=_('Used to generate url for new tilesource.'))
    #type = models.IntegerField(choices=TYPE_CHOICES, default=TYPE_TMS)

    def __init__(self, *args, **kwargs):
        super(TileOriginForm, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        return super(TileOriginForm, self).save(*args, **kwargs)

    class Meta():
        model = TileOrigin
        #exclude = ResourceBaseForm.Meta.exclude + (
        #    'content_type',
        #    'object_id',
        #    'doc_file',
        #    'extension',
        #    'doc_type',
        #    'doc_url')

class TileSourceForm(forms.ModelForm):

    #name = forms.CharField(max_length=100)
    #description = forms.CharField(max_length=400, help_text=_('Human-readable description of the services provided by this tile origin.'))
    #url = forms.CharField(max_length=400, help_text=_('Used to generate url for new tilesource.'))
    #type = models.IntegerField(choices=TYPE_CHOICES, default=TYPE_TMS)

    extensions = forms.MultipleChoiceField(required=True,widget=forms.CheckboxSelectMultiple, choices=IMAGE_EXTENSION_CHOICES, help_text = _("Select which extensions are accepted for the {ext} parameter in the url.  If none are selected, then the proxy selects any of those listed."))

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
        """
        Ensures the doc_file or the doc_url field is populated.
        """
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
