from django import forms
from escala.models import Escala
from evento.models import Evento
from escala.models import Funcao
from usuario.models import Usuario

class EscalaForm(forms.ModelForm):
    class Meta:
        model = Escala
        fields = ['usuario', 'funcao', 'confirmada']
        widgets = {
            'usuario': forms.Select(attrs={'class': 'form-control'}),
            'funcao': forms.Select(attrs={'class': 'form-control'}),
            'confirmada': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        evento = kwargs.pop('evento', None)
        super(EscalaForm, self).__init__(*args, **kwargs)

        if evento:
            self.fields['funcao'].queryset = Funcao.objects.filter(equipe__evento=evento)
            self.fields['usuario'].queryset = Usuario.objects.filter(membrosequipe__equipe__evento=evento)
