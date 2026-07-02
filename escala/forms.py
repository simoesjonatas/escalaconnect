from django import forms
from django.db import models
from django.utils.timezone import now
from escala.models import Escala,Funcao
from equipe.models import Equipe
from evento.models import Evento
from planejamento.models import Planejamento, PlanejamentoFuncao
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


class AplicarFuncoesEventosForm(forms.Form):
    FILTRO_EVENTOS_CHOICES = (
        ('equipe', 'Da equipe'),
        ('publicos', 'Somente públicos'),
        ('todos', 'Todos'),
    )

    planejamento = forms.ModelChoiceField(
        queryset=Planejamento.objects.none(),
        required=False,
        label="Planejamento",
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="Sem planejamento, vou escolher manualmente",
    )
    equipes = forms.ModelMultipleChoiceField(
        queryset=Equipe.objects.none(),
        required=False,
        label="Equipes",
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'team-checkbox-list'}),
    )
    eventos = forms.ModelMultipleChoiceField(
        queryset=Evento.objects.none(),
        label="Eventos",
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'event-checkbox-list'}),
    )
    filtro_eventos = forms.ChoiceField(
        choices=FILTRO_EVENTOS_CHOICES,
        required=False,
        initial='todos',
        label="Exibir eventos",
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_filtro_eventos'}),
    )
    funcoes = forms.ModelMultipleChoiceField(
        queryset=Funcao.objects.none(),
        required=False,
        label="Funções",
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'function-checkbox-list'}),
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user and (user.is_staff or user.is_superuser):
            equipes = Equipe.objects.all()
        elif user:
            equipes = Equipe.objects.filter(lideranca__usuario=user)
        else:
            equipes = Equipe.objects.none()

        equipes = equipes.distinct().order_by('nome')
        funcoes = Funcao.objects.filter(equipe__in=equipes).select_related('equipe').order_by('equipe__nome', 'nome')
        eventos = Evento.objects.filter(data_fim__gte=now())
        if user and not (user.is_staff or user.is_superuser):
            eventos = eventos.filter(
                models.Q(equipe__isnull=True) | models.Q(equipe__in=equipes)
            )
        eventos = eventos.select_related('equipe').distinct().order_by('data_inicio', 'nome')

        self.fields['equipes'].queryset = equipes
        self.fields['funcoes'].queryset = funcoes
        self.fields['eventos'].queryset = eventos
        self.fields['planejamento'].queryset = (
            Planejamento.objects
            .filter(funcoes__funcao__in=funcoes)
            .distinct()
            .order_by('nome')
        )

    def clean(self):
        cleaned_data = super().clean()
        equipes = cleaned_data.get('equipes')
        funcoes = cleaned_data.get('funcoes')
        planejamento = cleaned_data.get('planejamento')

        if equipes and funcoes:
            funcoes_fora = funcoes.exclude(equipe__in=equipes)
            if funcoes_fora.exists():
                raise forms.ValidationError("Selecione apenas funções das equipes escolhidas.")

        if not planejamento and not funcoes:
            raise forms.ValidationError("Escolha um planejamento ou selecione pelo menos uma função.")

        return cleaned_data

    def funcoes_selecionadas(self):
        planejamento = self.cleaned_data.get('planejamento')
        funcoes_ids = set(self.cleaned_data.get('funcoes').values_list('id', flat=True))

        if planejamento:
            ids_planejamento = PlanejamentoFuncao.objects.filter(
                planejamento=planejamento,
                funcao__in=self.fields['funcoes'].queryset,
            ).values_list('funcao_id', flat=True)
            funcoes_ids.update(ids_planejamento)

        return self.fields['funcoes'].queryset.filter(id__in=funcoes_ids)


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
