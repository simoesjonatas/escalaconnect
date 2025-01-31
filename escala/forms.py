from django import forms
from escala.models import Escala,Funcao
from equipe.models import Equipe
from usuario.models import Usuario

class MultiEscalaForm(forms.Form):
    equipe = forms.ModelChoiceField(
        queryset=Equipe.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'equipe-select'}),
        required=True
    )
    funcao = forms.ModelChoiceField(
        queryset=Funcao.objects.none(),  # Carregado dinamicamente via JS
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'funcao-select'}),
        required=True
    )


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

        # if evento:
        #     # Obtendo as equipes associadas ao evento
        #     equipes_do_evento = Equipe.objects.filter(evento=evento)

        #     # Filtrando funções que pertencem a essas equipes
        #     self.fields['funcao'].queryset = Funcao.objects.filter(equipe__in=equipes_do_evento)

        #     # Filtrando usuários que pertencem a essas equipes
        #     self.fields['usuario'].queryset = Usuario.objects.filter(membrosequipe__equipe__in=equipes_do_evento).distinct()


