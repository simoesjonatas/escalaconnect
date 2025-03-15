from django import forms
from django.core.exceptions import ValidationError
from .models import SolicitacaoTroca

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
        if SolicitacaoTroca.objects.filter(solicitante=self.user, escala_origem=self.escala, aprovada=False).exists():
            raise ValidationError('Você já possui uma solicitação pendente para esta escala.')
        return self.cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.solicitante = self.user
        instance.escala_origem = self.escala
        if commit:
            instance.save()
        return instance
