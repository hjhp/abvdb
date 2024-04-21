from django import forms
from .models import Abv

class AbvSubmitSingle(forms.ModelForm):
    class Meta:
        model = Abv
        fields = [
            "lwin11",
            "abv",
        ]
        labels = {
            "lwin11": "lwin11",
            "abv": "abv",
        }
        help_texts = {
            "lwin11": "11-digit integer",
            "abv": "Float from 0.0–100.0 with 1 decimal place, e.g. '0.0', '14.0', '100.0'.",
        }
        widgets = {
            "lwin11": forms.TextInput(),
            "abv": forms.TextInput(),
        }

class AbvSubmitFile(forms.Form):
    file = forms.FileField()
