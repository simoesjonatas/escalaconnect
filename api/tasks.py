from datetime import timedelta

import requests
from celery import shared_task
from django.conf import settings
from django.db.models import Exists, OuterRef
from django.utils import formats, timezone

from escala.models import Escala
from escalaconnect.push import notificar_push
from evento.models import Notification, NotificationAttempt

from . import push
from .models import Device


@shared_task(bind=True, autoretry_for=(requests.RequestException,), retry_backoff=True, max_retries=3)
def enviar_push_task(self, usuario_id, titulo, corpo, tipo, purpose, escala_id=None, throttle_horas=0):
    """Envia um push para todos os aparelhos ativos do usuário.

    Registra o envio em Notification/NotificationAttempt, como as tasks de e-mail.
    `tipo` e `escala_id` vão no payload para o app abrir a tela certa ao toque.
    """
    devices = list(Device.objects.filter(usuario_id=usuario_id, ativo=True))
    if not devices:
        return 'sem_aparelho'

    # filter().first() em vez de get_or_create: com escala nula o unique_together
    # não impede duplicatas no banco.
    filtro = dict(escala_id=escala_id, usuario_id=usuario_id, channel=Notification.CHANNEL_PUSH, purpose=purpose)
    notif = Notification.objects.filter(**filtro).first() or Notification.objects.create(**filtro, last_status='queued')

    if throttle_horas and notif.last_sent_at and timezone.now() - notif.last_sent_at < timezone.timedelta(hours=throttle_horas):
        NotificationAttempt.objects.create(
            notification=notif, status='skipped',
            error_message=f'Throttle: já enviado nas últimas {throttle_horas}h',
        )
        return 'throttled'

    mensagens = [
        {
            'to': device.expo_token,
            'title': titulo,
            'body': corpo,
            'sound': 'default',
            'data': {'tipo': tipo, 'escala_id': escala_id},
        }
        for device in devices
    ]
    try:
        tickets = push.enviar(mensagens)
    except requests.RequestException as erro:
        NotificationAttempt.objects.create(notification=notif, status='error', error_message=str(erro))
        notif.total_attempts += 1
        notif.last_status = 'error'
        notif.last_error = str(erro)
        notif.save(update_fields=['total_attempts', 'last_status', 'last_error', 'updated_at'])
        raise  # deixa o Celery re-tentar

    aguardando_recibo = {}
    for device, ticket in zip(devices, tickets):
        if ticket.get('status') == 'ok':
            aguardando_recibo[ticket['id']] = device.pk
        elif push.token_invalido(ticket):
            Device.objects.filter(pk=device.pk).update(ativo=False)

    status = 'sent' if aguardando_recibo else 'error'
    NotificationAttempt.objects.create(
        notification=notif, status=status,
        error_message='' if aguardando_recibo else 'Nenhum aparelho aceitou a notificação.',
        response_metadata={'tickets': tickets},
    )
    notif.total_attempts += 1
    if aguardando_recibo:
        notif.success_count += 1
        notif.last_sent_at = timezone.now()
    notif.last_status = status
    notif.save(update_fields=['total_attempts', 'success_count', 'last_sent_at', 'last_status', 'updated_at'])

    if aguardando_recibo:
        # A Expo só sabe se o aparelho ainda existe depois de entregar ao FCM/APNs.
        # Sem Celery Beat, a conferência é agendada aqui mesmo.
        verificar_recibos_push_task.apply_async(args=[aguardando_recibo], countdown=15 * 60)
    return status


@shared_task(autoretry_for=(requests.RequestException,), retry_backoff=True, max_retries=2)
def verificar_recibos_push_task(devices_por_ticket):
    """Desativa os aparelhos cujo recibo diz que o token não existe mais."""
    invalidos = [
        devices_por_ticket[ticket_id]
        for ticket_id, recibo in push.recibos(devices_por_ticket.keys()).items()
        if ticket_id in devices_por_ticket and push.token_invalido(recibo)
    ]
    return Device.objects.filter(pk__in=invalidos).update(ativo=False)


@shared_task
def lembrar_escalas_proximas():
    """Avisa pelo app quem está escalado em evento que começa nas próximas horas.

    Roda a cada 10 minutos (CELERY_BEAT_SCHEDULE). Cada voluntário recebe um único
    aviso por escala: quem já teve envio bem-sucedido fica de fora nas rodadas
    seguintes; se a escala mudar de pessoa, a nova é avisada. Só push, sem e-mail.
    """
    agora = timezone.now()
    ja_avisado = Notification.objects.filter(
        escala=OuterRef('pk'), usuario=OuterRef('usuario_id'),
        channel=Notification.CHANNEL_PUSH, purpose=Notification.PURPOSE_EVENT_SOON, success_count__gt=0,
    )
    escalas = (
        Escala.objects
        .filter(
            usuario__isnull=False,
            evento__data_inicio__gt=agora,
            evento__data_inicio__lte=agora + timedelta(hours=settings.LEMBRETE_EVENTO_HORAS),
        )
        .annotate(ja_avisado=Exists(ja_avisado))
        .filter(ja_avisado=False)
        .select_related('evento', 'funcao')
    )
    enfileirados = 0
    for escala in escalas:
        inicio = timezone.localtime(escala.evento.data_inicio)
        hoje = 'hoje ' if inicio.date() == timezone.localdate(agora) else ''
        corpo = f'{escala.evento.nome} · {escala.funcao.nome}'
        if not escala.confirmada:
            corpo += ' · Confirme sua presença'
        enfileirados += notificar_push(
            escala.usuario_id,
            f"Você serve {hoje}às {formats.date_format(inicio, 'H:i')}",
            corpo,
            # 'escalado' é o tipo que o app já sabe abrir na tela da escala.
            tipo='escalado', purpose=Notification.PURPOSE_EVENT_SOON, escala_id=escala.pk, throttle_horas=24,
        )
    return enfileirados
