from django import forms
from .models import Funcao
from equipe.models import Equipe

class FuncaoForm(forms.ModelForm):
    class Meta:
        model = Funcao
        fields = ['nome', 'equipe']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome da função'}),
            'equipe': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        equipe = kwargs.pop('equipe', None)
        super(FuncaoForm, self).__init__(*args, **kwargs)
        self.fields['equipe'].required = True
        
        if equipe:
            self.fields['equipe'].queryset = Equipe.objects.filter(pk=equipe.pk)
            self.fields['equipe'].initial = equipe
