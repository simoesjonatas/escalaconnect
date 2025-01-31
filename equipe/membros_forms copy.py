from django import forms
from .models import MembrosEquipe
from equipe.models import Equipe
from usuario.models import Usuario

class MembrosEquipeForm(forms.ModelForm):
    class Meta:
        model = MembrosEquipe
        fields = ['usuario', 'equipe']
        widgets = {
            'usuario': forms.Select(attrs={'class': 'form-control'}),
            'equipe': forms.Select(attrs={'class': 'form-control', 'readonly': True}),
        }
    
    def __init__(self, *args, **kwargs):
        equipe = kwargs.pop('equipe', None)
        super(MembrosEquipeForm, self).__init__(*args, **kwargs)
        self.fields['equipe'].required = True
        
        if equipe:
            self.fields['equipe'].queryset = Equipe.objects.filter(pk=equipe.pk)
            self.fields['equipe'].initial = equipe
            
    def clean_equipe(self):
        """ Garante que a equipe seja mantida no formulário """
        return self.instance.equipe if self.instance.pk else self.fields['equipe'].initial
