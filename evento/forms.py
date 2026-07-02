from django import forms
from django.utils import timezone
from django.utils.formats import date_format
from .models import Evento
from planejamento.models import Planejamento
from equipe.models import Equipe, Lideranca
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
        fields = ['nome', 'data_inicio', 'data_fim', 'observacao', 'equipe']
        widgets = {
            'data_inicio': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}, format='%Y-%m-%dT%H:%M'),
            'data_fim': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}, format='%Y-%m-%dT%H:%M'),
            'observacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'equipe': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super(EventoForm, self).__init__(*args, **kwargs)

        # Formatar as datas corretamente para preencher o input datetime-local
        if self.instance and self.instance.pk:
            if self.instance.data_inicio:
                self.fields['data_inicio'].initial = self.instance.data_inicio.strftime('%Y-%m-%dT%H:%M')
            if self.instance.data_fim:
                self.fields['data_fim'].initial = self.instance.data_fim.strftime('%Y-%m-%dT%H:%M')

        # Definir o campo observação como opcional
        self.fields['observacao'].required = False

        # Equipe é opcional: em branco = evento público (visível para todos).
        self.fields['equipe'].required = False
        self.fields['equipe'].empty_label = "Público (todos podem ver)"
        # Líderes só podem vincular o evento às equipes que lideram;
        # admin (staff/superuser) pode escolher qualquer equipe.
        if user is not None and not (user.is_superuser or user.is_staff):
            self.fields['equipe'].queryset = Equipe.objects.filter(
                id__in=Lideranca.objects.filter(usuario=user).values_list('equipe_id', flat=True)
            )

    def clean(self):
        cleaned_data = super().clean()
        data_inicio = cleaned_data.get('data_inicio')
        data_fim = cleaned_data.get('data_fim')
        
        if data_inicio and data_fim and data_inicio > data_fim:
            raise forms.ValidationError("A data de início não pode ser depois da data de fim.")
        
        return cleaned_data


class GerarEventosEmMassaForm(forms.Form):
    nome = forms.CharField(
        label="Nome do evento",
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    equipe = forms.ModelChoiceField(
        label="Equipe",
        queryset=Equipe.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    mes = forms.ChoiceField(
        label="Período",
        choices=(),
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    dias_da_semana = forms.MultipleChoiceField(
        label="Dias da semana",
        choices=DIAS_DA_SEMANA,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'weekday-checkboxes'}),
    )
    horario_inicio = forms.TimeField(
        label="Horário de início",
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
    )
    horario_fim = forms.TimeField(
        label="Horário de término",
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
    )
    observacao = forms.CharField(
        label="Observação",
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        hoje = timezone.localdate()
        proximo_mes = (hoje.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
        self.meses_permitidos = {
            hoje.strftime('%Y-%m'),
            proximo_mes.strftime('%Y-%m'),
            'ambos',
        }
        self.fields['mes'].choices = (
            (hoje.strftime('%Y-%m'), f"Mês atual — {date_format(hoje, 'F/Y')}"),
            (proximo_mes.strftime('%Y-%m'), f"Próximo mês — {date_format(proximo_mes, 'F/Y')}"),
            ('ambos', 'Mês atual e próximo mês'),
        )

        if user and (user.is_staff or user.is_superuser):
            equipes = Equipe.objects.all()
        elif user:
            equipes = Equipe.objects.filter(lideranca__usuario=user)
        else:
            equipes = Equipe.objects.none()
        self.fields['equipe'].queryset = equipes.distinct().order_by('nome')

    def clean_mes(self):
        mes = self.cleaned_data['mes']
        if mes not in self.meses_permitidos:
            raise forms.ValidationError("Escolha apenas o mês atual ou o próximo mês.")
        return mes

    def clean(self):
        cleaned_data = super().clean()
        inicio = cleaned_data.get('horario_inicio')
        fim = cleaned_data.get('horario_fim')
        if inicio and fim and fim <= inicio:
            raise forms.ValidationError("O horário de término deve ser posterior ao início.")
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
    data_inicial = forms.DateField(
        label="Data Inicial (opcional - início da criação dos eventos recorrentes)",
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

class GerarCultosMensaisForm(forms.Form):
    mes = forms.IntegerField(
        label="Mês inicial",
        min_value=1,
        max_value=12,
        initial=datetime.date.today().month,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    ano = forms.IntegerField(
        label="Ano inicial",
        min_value=2000,
        max_value=2100,
        initial=datetime.date.today().year,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    quantidade_meses = forms.IntegerField(
        label="Quantidade de meses",
        min_value=1,
        max_value=24,
        initial=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    ignorar_existentes = forms.BooleanField(
        label="Não criar eventos que já existem",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

class EventoComPlanejamentoForm(forms.ModelForm):
    planejamento = forms.ModelChoiceField(
        queryset=Planejamento.objects.all(),
        label="Planejamento",
        required=False,
        help_text="Selecione um planejamento para este evento",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Evento
        fields = ['nome', 'data_inicio', 'data_fim', 'observacao', 'planejamento']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'data_inicio': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}, format='%Y-%m-%dT%H:%M'),
            'data_fim': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}, format='%Y-%m-%dT%H:%M'),
            'observacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        data_inicio = cleaned_data.get('data_inicio')
        data_fim = cleaned_data.get('data_fim')

        if data_inicio and data_fim and data_inicio > data_fim:
            raise forms.ValidationError("A data de início não pode ser depois da data de fim.")

        return cleaned_data
