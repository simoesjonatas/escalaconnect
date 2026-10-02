from django import forms
from django.core.exceptions import ValidationError
from .models import Desistencia
from .services import RegraDeNegocio, validar_impedimento
from datetime import datetime
from django.utils import timezone


class DesistenciaForm(forms.ModelForm):
    class Meta:
        model = Desistencia
        fields = ['motivo']  # Somente o motivo é editável pelo usuário
        widgets = {
            'motivo': forms.Textarea(attrs={'cols': 40, 'rows': 5}),
        }

    def __init__(self, *args, user=None, escala=None, **kwargs):
        self.user = user
        self.escala = escala
        super(DesistenciaForm, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        motivo = cleaned_data.get('motivo')
        
        # Regras (dono, evento já iniciado, desistência repetida) compartilhadas com a API do app.
        if self.escala:
            try:
                validar_impedimento(self.escala, self.user)
            except RegraDeNegocio as erro:
                raise ValidationError(str(erro))

        return cleaned_data
