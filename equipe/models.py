from django.db import models
from django.conf import settings
from django.db.models import QuerySet


class Equipe(models.Model):
    nome = models.CharField(max_length=255)
    def __str__(self):
        return self.nome

# class AprovadoMembrosQuerySet(models.QuerySet):
#     def aprovados(self):
#         return self.filter(aprovado=True)
# class AprovadoMembrosManager(models.Manager.from_queryset(AprovadoMembrosQuerySet)):
#     pass

class MembrosEquipe(models.Model):
    equipe = models.ForeignKey(Equipe, on_delete=models.CASCADE, null=False, blank=False, related_name='membros')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,null=False, blank=False)
    aprovado = models.BooleanField(default=False)
        
    # objects = models.Manager()  # O manager padrão sem modificações
    # aprovados = AprovadoMembrosManager()  # O manager customizado para membros aprovados

    class Meta:
        unique_together = ('equipe', 'usuario')  # Impede duplicação no banco de dados

    def __str__(self):
        return f"{self.usuario} - {self.equipe}"
    
    # def __str__(self):
    #     status = "Aprovado" if self.aprovado else "Pendente"
    #     return f"{self.usuario} - {self.equipe} ({status})"


class Lideranca(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,null=False, blank=False)
    equipe = models.ForeignKey('equipe.Equipe', on_delete=models.CASCADE,null=False, blank=False)
    
    class Meta:
        unique_together = ('equipe', 'usuario')  # Impede duplicação no banco de dados

    def __str__(self):
        return f"Líder: {self.usuario} - Equipe: {self.equipe}"


