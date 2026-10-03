from django.conf import settings
from django.db import models


class Device(models.Model):
    """Aparelho com o app instalado, para onde vão as notificações push de um usuário."""
    PLATAFORMAS = [('android', 'Android'), ('ios', 'iOS')]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='devices')
    expo_token = models.CharField(max_length=255, unique=True)
    plataforma = models.CharField(max_length=10, choices=PLATAFORMAS)
    nome_aparelho = models.CharField(max_length=100, blank=True)
    app_versao = models.CharField(max_length=30, blank=True)
    # Desativado no logout ou quando a Expo informa que o token não existe mais.
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    ultimo_uso = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=['usuario', 'ativo'])]

    def __str__(self):
        return f"{self.usuario} - {self.nome_aparelho or self.plataforma}"
