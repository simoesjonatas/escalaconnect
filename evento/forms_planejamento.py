from django import forms
from equipe.models import Equipe
from escala.models import Funcao
from evento.models import Evento

class PlanejamentoEquipeForm(forms.Form):
    equipe = forms.ModelChoiceField(
        queryset=Equipe.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Equipe"
    )
    eventos = forms.ModelMultipleChoiceField(
        queryset=Evento.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
        label="Eventos"
    )
    funcoes = forms.ModelMultipleChoiceField(
        queryset=Funcao.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
        label="Funções"
    )

    def __init__(self, *args, **kwargs):
        equipe_id = kwargs.pop('equipe_id', None)
        super(PlanejamentoEquipeForm, self).__init__(*args, **kwargs)

        # Se uma equipe foi selecionada, filtra as funções dessa equipe
        if equipe_id:
            self.fields['funcoes'].queryset = Funcao.objects.filter(equipe_id=equipe_id)
