from django import forms
from .models import Equipe

class EquipeForm(forms.ModelForm):
    class Meta:
        model = Equipe
        fields = ['nome']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome da Equipe'}),
        }

    def clean_nome(self):
        nome = self.cleaned_data.get('nome')
        if not nome.strip():
            raise forms.ValidationError("O nome da equipe não pode estar vazio.")
        return nome
