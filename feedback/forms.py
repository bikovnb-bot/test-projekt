from django import forms
from .models import Suggestion, Bug

class SuggestionForm(forms.ModelForm):
    class Meta:
        model = Suggestion
        fields = ['title', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }

class BugForm(forms.ModelForm):
    class Meta:
        model = Bug
        fields = ['title', 'description', 'steps_to_reproduce']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'steps_to_reproduce': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }