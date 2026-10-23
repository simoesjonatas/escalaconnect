from escala.models import Escala
from evento.models import Notification

from . import mensagens_push
from .push import notificar_push
from .tasks import enviar_email_confirmacao_task


def pedir_confirmacao(evento, lembrete=False):
    """Pede a confirmação de quem ainda não confirmou presença no evento.

    Enfileira o e-mail (para quem tem e-mail) e o push (para quem tem o app).
    Devolve quantos e-mails foram enfileirados.
    """
    escalas = (
        Escala.objects
        .filter(evento=evento, confirmada=False, usuario__isnull=False)
        .select_related('usuario', 'funcao')
    )
    emails = 0
    for escala in escalas:
        if escala.usuario.email:
            enviar_email_confirmacao_task.delay(escala.id)
            emails += 1
        notificar_push(
            escala.usuario_id, *mensagens_push.pedido_de_confirmacao(escala),
            tipo='confirmar_escala',
            purpose=Notification.PURPOSE_REMINDER if lembrete else Notification.PURPOSE_CONFIRM,
            escala_id=escala.pk,
            throttle_horas=6,  # mesmo intervalo mínimo do e-mail
        )
    return emails
