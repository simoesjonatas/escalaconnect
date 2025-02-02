from django import forms
from .models import Disponivel

class DisponivelForm(forms.ModelForm):
    class Meta:
        model = Disponivel
        fields = ['data_inicio', 'data_fim']
        widgets = {
            'data_inicio': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}, format='%Y-%m-%dT%H:%M'),
            'data_fim': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}, format='%Y-%m-%dT%H:%M'),
        }
