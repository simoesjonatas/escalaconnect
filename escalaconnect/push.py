from django.db import transaction
from django.utils import formats, timezone


def notificar_push(usuario_id, titulo, corpo, tipo, purpose, escala_id=None, throttle_horas=0):
    """Enfileira um push para o usuário, depois do commit da transação atual.

    Não faz nada se o usuário não tem aparelho com o app (a maioria, no começo).
    Import tardio de api.*: os services dos outros apps chamam esta função e a
    API depende deles, não o contrário.
    """
    if not usuario_id:
        return
    from api.models import Device
    from api.tasks import enviar_push_task

    if not Device.objects.filter(usuario_id=usuario_id, ativo=True).exists():
        return
    transaction.on_commit(lambda: enviar_push_task.delay(
        usuario_id, titulo, corpo, tipo, purpose, escala_id=escala_id, throttle_horas=throttle_horas))


def quando(evento):
    """'dom, 04/10 às 19:00', no fuso local, para o corpo das notificações."""
    return formats.date_format(timezone.localtime(evento.data_inicio), 'D, d/m \\à\\s H:i')
