from django.db import models
from django.conf import settings
from evento.models import Evento

class Disponivel(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    evento = models.ForeignKey(Evento, on_delete=models.SET_NULL, null=True, blank= True)
    data_inicio = models.DateTimeField()
    data_fim = models.DateTimeField()
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.usuario.username} disponível de {self.data_inicio} até {self.data_fim}"
