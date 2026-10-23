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


class Aviso(models.Model):
    """Notificação guardada para a caixa de avisos do app (o sino do Início).

    Criada a cada notificar_push, mesmo para quem não recebe push (sem aparelho ou
    com a permissão negada). Apagada depois de 60 dias (api.tasks.limpar_avisos_antigos).
    """
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='avisos')
    titulo = models.CharField(max_length=120)
    corpo = models.CharField(max_length=255)
    # Mesmo `tipo` do payload do push: diz qual tela o app abre ao tocar.
    tipo = models.CharField(max_length=40)
    purpose = models.CharField(max_length=40)
    escala = models.ForeignKey('escala.Escala', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    criado_em = models.DateTimeField(auto_now_add=True)
    lido_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-criado_em']
        indexes = [models.Index(fields=['usuario', 'lido_em'])]

    def __str__(self):
        return f"{self.usuario} - {self.titulo}"
