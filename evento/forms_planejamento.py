from django import forms
from equipe.models import Equipe
from escala.models import Funcao
from evento.models import Evento
from planejamento.models import Planejamento
from django.utils.timezone import now

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


class AplicarPlanejamentoEventosForm(forms.Form):
    planejamento = forms.ModelChoiceField(
        queryset=Planejamento.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Planejamento"
    )
    eventos = forms.ModelMultipleChoiceField(
        queryset=Evento.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        label="Eventos"
    )

    def __init__(self, *args, **kwargs):
        planejamento_id = kwargs.pop('planejamento_id', None)
        super().__init__(*args, **kwargs)

        today = now().date()
        self.fields['eventos'].queryset = Evento.objects.filter(
            data_inicio__date__gte=today
        ).order_by('data_inicio')

        if planejamento_id:
            self.fields['planejamento'].initial = planejamento_id
