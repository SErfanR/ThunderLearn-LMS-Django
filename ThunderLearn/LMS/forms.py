from ckeditor.widgets import CKEditorWidget
from django import forms
from .models import Presentation


class PresentationForm(forms.ModelForm):
    des = forms.CharField(widget=CKEditorWidget())
    class Meta:
        model = Presentation
        fields = ['title', 'classroom', 'des']