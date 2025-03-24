from django.db import models
from django.contrib.auth.models import AbstractUser
from .utils import validate_cpf
from equipe.models import Lideranca, Equipe, MembrosEquipe
from django.utils import timezone

import uuid


class Usuario(AbstractUser):
    telefone = models.CharField(max_length=255, blank=True, null=True)
    aniversario = models.DateTimeField(blank=True, null=True)
    batismo = models.DateTimeField(blank=True, null=True)
    is_first_login = models.BooleanField(default=True)

    # cpf = models.CharField(max_length=255, unique=True)
    cpf = models.CharField(
        max_length=11,  # CPF tem 11 dígitos numéricos
        unique=True,
        validators=[validate_cpf],
        help_text="Digite apenas os números do CPF (sem pontos ou traços)."
    )
    
    def __str__(self):
        return f"{self.username} ({self.email})"

    def is_leader(self):
        return Lideranca.objects.filter(usuario=self).exists()
    
    def is_in_team(self):
        # Verifica se o usuário é superuser ou staff, o que automaticamente o qualifica como 'em uma equipe'
        if self.is_staff or self.is_superuser:
            return True

        # Verifica se o usuário é membro aprovado de pelo menos uma equipe
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
