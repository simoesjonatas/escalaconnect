from django import forms
from django.core.exceptions import ValidationError
from .models import SolicitacaoTroca
from .services import RegraDeNegocio, validar_solicitacao_troca

class DesistenciaForm(forms.ModelForm):
    class Meta:
        model = SolicitacaoTroca
        fields = ['tipo_solicitacao']
        widgets = {
            'tipo_solicitacao': forms.HiddenInput()
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.escala = kwargs.pop('escala', None)
        super().__init__(*args, **kwargs)
        self.fields['tipo_solicitacao'].initial = 'desistencia'

    def clean(self):
        super().clean()
        # Verifica se já existe uma solicitação pendente não aprovada
        # (regra compartilhada com a API do app)
        if self.escala:
            try:
                validar_solicitacao_troca(self.escala, self.user)
            except RegraDeNegocio as erro:
                raise ValidationError(str(erro))
        return self.cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.solicitante = self.user
        instance.escala_origem = self.escala
        if commit:
            instance.save()
        return instance
