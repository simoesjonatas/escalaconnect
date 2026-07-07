from django.db import models
from django.contrib.auth.models import AbstractUser
from django.apps import apps
from .utils import validate_cpf, formatar_telefone
from django.utils import timezone

import uuid


class Usuario(AbstractUser):
    telefone = models.CharField(max_length=255, blank=True, null=True)
    aniversario = models.DateField(blank=True, null=True)
    batismo = models.DateField(blank=True, null=True)
    is_first_login = models.BooleanField(default=True)
    termo_aceito_em = models.DateTimeField(blank=True, null=True)
    ultima_atividade = models.DateTimeField(blank=True, null=True)

    # cpf = models.CharField(max_length=255, unique=True)
    cpf = models.CharField(
        max_length=11,  # CPF tem 11 dígitos numéricos
        unique=True,
        validators=[validate_cpf],
        help_text="Digite apenas os números do CPF (sem pontos ou traços)."
    )
    
    @property
    def telefone_formatado(self):
        return formatar_telefone(self.telefone)

    def __str__(self):
        return f"{self.username} ({self.email})"

    def is_leader(self):
        Lideranca = apps.get_model('equipe', 'Lideranca')
        return Lideranca.objects.filter(usuario=self).exists()

    def is_in_team(self):
        # Verifica se o usuário é superuser ou staff, o que automaticamente o qualifica como 'em uma equipe'
        if self.is_staff or self.is_superuser:
            return True

        # Verifica se o usuário é membro aprovado de pelo menos uma equipe
        MembrosEquipe = apps.get_model('equipe', 'MembrosEquipe')
        return MembrosEquipe.objects.filter(usuario=self, aprovado=True).exists()



class PasswordResetRequest(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    hash = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    reset_at = models.DateTimeField(blank=True, null=True)
    is_used = models.BooleanField(default=False)

    class Meta:
        indexes = [models.Index(fields=['hash', 'is_used', 'created_at'])]

    def hash_valido(self):
        limite_tempo = timezone.now() - timezone.timedelta(minutes=15)
        return not self.is_used and self.created_at >= limite_tempo

    def __str__(self):
        return f"Pedido para {self.usuario.username} ({'usado' if self.is_used else 'ativo'})"


class RegistroLogin(models.Model):
    """Um registro por login bem-sucedido, para as métricas de uso."""
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='registros_login')
    data_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['data_hora'])]

    def __str__(self):
        return f"Login de {self.usuario.username} em {self.data_hora:%d/%m/%Y %H:%M}"


class AtividadeDiaria(models.Model):
    """No máximo um registro por usuário por dia com atividade autenticada."""
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='atividades_diarias')
    data = models.DateField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['usuario', 'data'], name='atividade_unica_usuario_data'),
        ]
        indexes = [models.Index(fields=['data'])]

    def __str__(self):
        return f"{self.usuario.username} ativo em {self.data:%d/%m/%Y}"
