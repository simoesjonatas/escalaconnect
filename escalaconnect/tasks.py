from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone, formats
from django.urls import reverse
from django.conf import settings

from escala.models import Escala
from evento.models import Notification, NotificationAttempt  # <- agora vem de evento.models

# @shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3, rate_limit="30/m")
def enviar_email_confirmacao_task(self, escala_id: int):
    # carrega escala + relacionamentos
    escala = (
        Escala.objects
        .select_related("usuario", "evento", "funcao", "funcao__equipe")
        .get(pk=escala_id)
    )
    usuario = escala.usuario
    evento = escala.evento

    # 1) registro de acompanhamento da notificação (1 por combinação)
    notif, _ = Notification.objects.get_or_create(
        escala=escala,
        usuario=usuario,
        channel=Notification.CHANNEL_EMAIL,
        purpose=Notification.PURPOSE_CONFIRM,
        defaults={"last_status": "queued"},
    )

    # throttling: não enviar se já mandou há < 6h
    if notif.last_sent_at and (timezone.now() - notif.last_sent_at).total_seconds() < 6 * 3600:
        NotificationAttempt.objects.create(
            notification=notif, status="skipped",
            error_message="Throttle: já enviado nas últimas 6h",
            response_metadata={"reason": "throttle_6h"}
        )
        # notif.last_status = "skipped"
        notif.last_error = "Throttle 6h"
        notif.save(update_fields=["last_status", "last_error", "updated_at"])
        return "throttled"

    # 2) contexto do e-mail (formatos pt-BR)
    evento_data = formats.date_format(evento.data_inicio, "l, d \\d\\e F \\d\\e Y", use_l10n=True)
    evento_hora = formats.date_format(evento.data_inicio, "H:i", use_l10n=True)

    confirm_url = _build_confirm_url(evento_id=evento.id, escala_id=escala.id)

    contexto = {
        "usuario_nome": (getattr(usuario, "first_name", "") or usuario.get_username()) if usuario else "Colaborador(a)",
        "evento_nome": evento.nome,
        "evento_data": evento_data,
        "evento_hora": evento_hora,
        "equipe_nome": getattr(escala.funcao.equipe, "nome", None) if escala.funcao else None,
        "funcao_nome": getattr(escala.funcao, "nome", None),
        "confirm_url": confirm_url,
    }

    assunto = f"Confirmação de Escala: {evento.nome} - ESCALA CONNECT - PIBVP"
    corpo_html = render_to_string("email/confirmacao_email.html", contexto)
    corpo_txt = f"{contexto['usuario_nome']}, confirme sua presença: {confirm_url}"

    # 3) envio + log
    try:
        to_email = [usuario.email] if (usuario and usuario.email) else []
        if not to_email:
            raise Exception("Usuário sem e-mail cadastrado.")

        msg = EmailMultiAlternatives(subject=assunto, body=corpo_txt, to=to_email)
        msg.attach_alternative(corpo_html, "text/html")
        send_result = msg.send()  # 1=ok, 0=nok

        status = "sent" if send_result else "error"
        error_message = "" if send_result else "EmailBackend retornou 0 (nenhum destinatário aceito)."

        NotificationAttempt.objects.create(
            notification=notif, status=status,
            error_message=error_message,
            response_metadata={"send_result": send_result},
        )

        notif.total_attempts += 1
        if status == "sent":
            notif.success_count += 1
            notif.last_sent_at = timezone.now()
        notif.last_status = status
        notif.last_error = error_message
        notif.last_response = str({"send_result": send_result})
        notif.save(update_fields=[
            "total_attempts", "success_count", "last_sent_at",
            "last_status", "last_error", "last_response", "updated_at"
        ])

        if status != "sent":
            raise Exception(error_message)

        return "ok"

    except Exception as e:
        NotificationAttempt.objects.create(
            notification=notif, status="error", error_message=str(e)
        )
        notif.total_attempts += 1
        notif.last_status = "error"
        notif.last_error = str(e)
        notif.save(update_fields=["total_attempts", "last_status", "last_error", "updated_at"])
        raise  # deixa o Celery re-tentar

def _build_confirm_url(evento_id: int, escala_id: int) -> str:
    base = getattr(settings, "SITE_URL", "https://connect.pibvp.org.br")
    path = reverse("minhas_escalas_confirmar", kwargs={"evento_id": evento_id, "escala_id": escala_id})
    return f"{base}{path}"
