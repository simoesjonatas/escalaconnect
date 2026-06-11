from django.db import models
from django.conf import settings
from evento.models import Evento

class Ocupado(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    # motivo = models.TextField(null= True, blank=True, max_length=255)
    evento = models.ForeignKey(Evento, on_delete=models.SET_NULL, null=True, blank= True)
    data_inicio = models.DateTimeField()
    data_fim = models.DateTimeField()
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['usuario', 'data_inicio', 'data_fim']),
        ]

    def __str__(self):
        return f"{self.usuario.username} - {self.data_inicio} até {self.data_fim}"
