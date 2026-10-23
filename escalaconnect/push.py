from datetime import timedelta

from django.db import transaction
from django.utils import formats, timezone


def notificar_push(usuario_id, titulo, corpo, tipo, purpose, escala_id=None, throttle_horas=0):
    """Guarda o aviso na caixa do app e enfileira o push, depois do commit da transação atual.

    O aviso fica guardado mesmo sem aparelho; o push só sai para quem tem o app.
    Devolve True só quando enfileirou o push. Import tardio de api.*: os services
    dos outros apps chamam esta função e a API depende deles, não o contrário.
    """
    if not usuario_id:
        return False
    from api.models import Aviso, Device
    from api.tasks import enviar_push_task

    repetido = throttle_horas and Aviso.objects.filter(
        usuario_id=usuario_id, escala_id=escala_id, purpose=purpose,
        criado_em__gte=timezone.now() - timedelta(hours=throttle_horas),
    ).exists()
    if not repetido:
        Aviso.objects.create(
            usuario_id=usuario_id, titulo=titulo[:120], corpo=corpo[:255], tipo=tipo, purpose=purpose,
            escala_id=escala_id,
        )

    if not Device.objects.filter(usuario_id=usuario_id, ativo=True).exists():
        return False
    transaction.on_commit(lambda: enviar_push_task.delay(
        usuario_id, titulo, corpo, tipo, purpose, escala_id=escala_id, throttle_horas=throttle_horas))
    return True


def quando(evento):
    """'dom, 04/10 às 19:00', no fuso local, para o corpo das notificações."""
    return formats.date_format(timezone.localtime(evento.data_inicio), 'D, d/m \\à\\s H:i')
