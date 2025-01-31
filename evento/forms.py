from django import forms
from .models import Evento
from planejamento.models import Planejamento
import datetime

DIAS_DA_SEMANA = [
    (0, "Segunda-feira"),
    (1, "Terça-feira"),
    (2, "Quarta-feira"),
    (3, "Quinta-feira"),
    (4, "Sexta-feira"),
    (5, "Sábado"),
    (6, "Domingo"),
]

class EventoForm(forms.ModelForm):
    class Meta:
        model = Evento
        fields = ['nome', 'data_inicio', 'data_fim', 'observacao']
        widgets = {
            'data_inicio': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}, format='%Y-%m-%dT%H:%M'),
            'data_fim': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}, format='%Y-%m-%dT%H:%M'),
            'observacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super(EventoForm, self).__init__(*args, **kwargs)
        
        # Formatar as datas corretamente para preencher o input datetime-local
        if self.instance and self.instance.pk:
            if self.instance.data_inicio:
                self.fields['data_inicio'].initial = self.instance.data_inicio.strftime('%Y-%m-%dT%H:%M')
            if self.instance.data_fim:
                self.fields['data_fim'].initial = self.instance.data_fim.strftime('%Y-%m-%dT%H:%M')
        
        # Definir o campo observação como opcional
        self.fields['observacao'].required = False

    def clean(self):
        cleaned_data = super().clean()
        data_inicio = cleaned_data.get('data_inicio')
        data_fim = cleaned_data.get('data_fim')
        
        if data_inicio and data_fim and data_inicio > data_fim:
            raise forms.ValidationError("A data de início não pode ser depois da data de fim.")
        
        return cleaned_data


class EventoRecorrenteForm(forms.Form):
    nome = forms.CharField(label="Nome do Evento", max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    data_inicio = forms.TimeField(label="Horário de Início", widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}))
    data_fim = forms.TimeField(label="Horário de Fim", widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}))
    dia_da_semana = forms.ChoiceField(label="Dia da Semana", choices=DIAS_DA_SEMANA, widget=forms.Select(attrs={'class': 'form-control'}))
    repeticoes = forms.IntegerField(label="Repetir por (semanas)", min_value=1, max_value=52, initial=24, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    planejamento = forms.ModelChoiceField(
        label="Planejamento Base",
        queryset=Planejamento.objects.all(),
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
