from django.db import models
from django.conf import settings


class Evento(models.Model):
    nome = models.CharField(max_length=255)
    data_inicio = models.DateTimeField()
    data_fim = models.DateTimeField()
    observacao = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.nome} ({self.data_inicio} - {self.data_fim})"


class Disponibilidade(models.Model):
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"Usuário: {self.usuario} - Evento: {self.evento}"

