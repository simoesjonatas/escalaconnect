from datetime import datetime, time, timedelta

import requests
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from escala.models import Escala
from escalaconnect import mensagens_push
from escalaconnect.push import notificar_push
from evento.models import Notification, NotificationAttempt

from . import push
from .models import Aviso, Device


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

    # Número no ícone do app: avisos ainda não lidos na caixa do app.
    nao_lidos = Aviso.objects.filter(usuario_id=usuario_id, lido_em__isnull=True).count()
    mensagens = [
        {
            'to': device.expo_token,
            'title': titulo,
            'body': corpo,
            'sound': 'default',
            'badge': nao_lidos,
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


def _avisos_da_escala(escala):
    """[(momento, purpose, mensagem)] em ordem cronológica, conforme a confirmação atual.

    Quem não confirmou: pedido de confirmação na véspera, lembrete do dia (só cultos
    da tarde/noite, já que os da manhã têm o pedido na véspera) e última chamada.
    Quem confirmou: só o lembrete, sem tom de cobrança.
    """
    inicio = timezone.localtime(escala.evento.data_inicio)
    vespera = inicio.date() - timedelta(days=1)

    def no_horario(dia, hora):
        return timezone.make_aware(datetime.combine(dia, time(hora)))

    if inicio.hour < settings.LEMBRETE_CORTE_HORA:
        lembrete = no_horario(vespera, settings.LEMBRETE_VESPERA_HORA)
    else:
        lembrete = no_horario(inicio.date(), settings.LEMBRETE_DIA_HORA)
    lembrete = (lembrete, Notification.PURPOSE_DAY_REMINDER, mensagens_push.lembrete_da_escala)

    if escala.confirmada:
        return [lembrete]
    avisos = [(no_horario(vespera, settings.CONFIRMACAO_VESPERA_HORA),
               Notification.PURPOSE_CONFIRM_EVE, mensagens_push.pedido_de_confirmacao)]
    if lembrete[0].date() == inicio.date():
        avisos.append(lembrete)
    avisos.append((inicio - timedelta(hours=settings.LEMBRETE_EVENTO_HORAS),
                   Notification.PURPOSE_EVENT_SOON, mensagens_push.ultima_chamada))
    return sorted(avisos, key=lambda aviso: aviso[0])


@shared_task
def lembretes_de_escala():
    """Lembretes pelo app de quem está escalado nos próximos dois dias (ver settings).

    Roda a cada 10 minutos (CELERY_BEAT_SCHEDULE). Em cada escala, só o aviso mais
    recente que já venceu é enviado, e uma única vez: se o beat ficou parado ou a
    pessoa foi escalada em cima da hora, ela recebe só o aviso que faz sentido agora,
    não todos os atrasados. Se a escala mudar de pessoa, a nova é avisada. Só push.
    """
    agora = timezone.now()
    escalas = list(
        Escala.objects
        .filter(usuario__isnull=False, evento__data_inicio__gt=agora,
                evento__data_inicio__lte=agora + timedelta(hours=48))
        .select_related('evento', 'funcao')
    )
    enviados = set(
        Notification.objects
        .filter(escala__in=escalas, channel=Notification.CHANNEL_PUSH, success_count__gt=0)
        .values_list('escala_id', 'usuario_id', 'purpose')
    )
    enfileirados = 0
    for escala in escalas:
        vencidos = [aviso for aviso in _avisos_da_escala(escala) if aviso[0] <= agora]
        if not vencidos:
            continue
        _, purpose, mensagem = vencidos[-1]
        if (escala.pk, escala.usuario_id, purpose) in enviados:
            continue
        enfileirados += notificar_push(
            escala.usuario_id, *mensagem(escala),
            # 'escalado' é o tipo que o app já sabe abrir na tela da escala.
            tipo='escalado', purpose=purpose, escala_id=escala.pk, throttle_horas=24,
        )
    return enfileirados


DIAS_DE_AVISOS = 60


@shared_task
def limpar_avisos_antigos():
    """Apaga da caixa do app os avisos com mais de 60 dias (roda uma vez por dia)."""
    apagados, _ = Aviso.objects.filter(criado_em__lt=timezone.now() - timedelta(days=DIAS_DE_AVISOS)).delete()
    return apagados
