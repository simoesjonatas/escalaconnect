from django.db import models
from django.conf import settings
from django.utils.formats import date_format



class Evento(models.Model):
    nome = models.CharField(max_length=255)
    data_inicio = models.DateTimeField()
    data_fim = models.DateTimeField()
    observacao = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.nome} ({self.data_inicio} - {self.data_fim})"
    
    def data_inicio_com_dia_da_semana(self):
        """
        Retorna a data de início do evento incluindo o nome do dia da semana.
        """
        # Formatando a data para incluir o dia da semana em português
        return date_format(self.data_inicio, format="l, d F Y", use_l10n=True)
    def has_issues(self):
        """
        Verifica se há solicitações de troca não aprovadas ou desistências não aprovadas
        em qualquer escala deste evento.
        """
        from escala.models import Escala  # Import here to avoid circular dependency
        escalas = Escala.objects.filter(evento=self)
        for escala in escalas:
            if escala.has_solicitacao_troca_aberta() or escala.has_impedimento():
                return True
        return False


class Disponibilidade(models.Model):
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"Usuário: {self.usuario} - Evento: {self.evento}"

