from django import forms
from datetime import timedelta, date
from django.utils.timezone import now
from equipe.models import Equipe
from escala.models import Funcao
from evento.models import Evento

class GeradorEventosPlanejamentoForm(forms.Form):
    nome_evento = forms.CharField(
        label="Nome do Evento",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    horario_inicio = forms.TimeField(
        label="Horário de Início",
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'})
    )
    horario_fim = forms.TimeField(
        label="Horário de Fim",
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'})
    )
    dia_semana = forms.ChoiceField(
        choices=[
            ('0', 'Domingo'),
            ('1', 'Segunda-feira'),
            ('2', 'Terça-feira'),
            ('3', 'Quarta-feira'),
            ('4', 'Quinta-feira'),
            ('5', 'Sexta-feira'),
            ('6', 'Sábado'),
        ],
        label="Dia da Semana",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    duracao_meses = forms.IntegerField(
        label="Duração (em meses)",
        min_value=1,
        max_value=12,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    equipe = forms.ModelChoiceField(
        queryset=Equipe.objects.all(),
        label="Equipe",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    funcoes = forms.ModelMultipleChoiceField(
        queryset=Funcao.objects.all(),
        label="Funções da Equipe",
        widget=forms.SelectMultiple(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        super(GeradorEventosPlanejamentoForm, self).__init__(*args, **kwargs)
        self.fields['funcoes'].queryset = Funcao.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        horario_inicio = cleaned_data.get("horario_inicio")
        horario_fim = cleaned_data.get("horario_fim")

        if horario_inicio and horario_fim and horario_inicio >= horario_fim:
            self.add_error("horario_fim", "O horário de fim deve ser maior que o horário de início.")

        return cleaned_data
