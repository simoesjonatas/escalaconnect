from django import forms
from django.core.exceptions import ValidationError
from .models import Desistencia
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
        
        # Verifica se a escala já começou
        if self.escala and self.escala.evento.data_inicio <= timezone.now():
            raise ValidationError("Não é possível sinalizar desistência após o início do evento.")

        # Verificar se já existe uma desistência para a mesma escala e usuário
        if Desistencia.objects.filter(escala=self.escala, usuario=self.user, aprovada = False).exists():
            raise ValidationError("Você já sinalizou desistência para esta escala.")

        return cleaned_data
