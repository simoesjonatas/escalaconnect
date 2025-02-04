from django.db import models
from django.contrib.auth.models import AbstractUser
from .utils import validate_cpf
from equipe.models import Lideranca

class Usuario(AbstractUser):
    telefone = models.CharField(max_length=255, blank=True, null=True)
    aniversario = models.DateTimeField(blank=True, null=True)
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
