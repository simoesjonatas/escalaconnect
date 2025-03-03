from django import forms
from .models import Ocupado

class OcupadoForm(forms.ModelForm):
    class Meta:
        model = Ocupado
        fields = ['data_inicio', 'data_fim'] #'motivo'
        widgets = {
            # 'motivo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Motivo da indisponibilidade, não obrigatório'}),
            'data_inicio': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}, format='%Y-%m-%dT%H:%M'),
            'data_fim': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}, format='%Y-%m-%dT%H:%M'),
        }

