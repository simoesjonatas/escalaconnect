"""Escalas no formato iCalendar (.ics), para o site e para o link de agenda do app.

O link do app não tem sessão: leva um token assinado com o id do usuário e um
pedaço do hash da senha, para que trocar a senha invalide links antigos.
"""
from datetime import timezone as datetime_timezone

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.http import HttpResponse
from django.urls import reverse
from django.utils.crypto import constant_time_compare
from django.utils.timezone import now

SALT_AGENDA = 'escala.agenda'


def _ics_escape(text):
    """Escapa caracteres especiais de texto para o formato iCalendar."""
    return (
        (text or '')
        .replace('\\', '\\\\')
        .replace(';', '\\;')
        .replace(',', '\\,')
        .replace('\n', '\\n')
    )


def _ics_datetime(dt):
    """Formata um datetime aware em UTC no padrão iCalendar (ex.: 20260611T130000Z)."""
    return dt.astimezone(datetime_timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def gerar_ics(escalas, nome='Minhas Escalas'):
    """Conteúdo .ics com um evento por escala (espera select_related de evento e funcao__equipe)."""
    linhas = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//Escala Connect//PT-BR//',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        f'X-WR-CALNAME:{_ics_escape(nome)}',
        # Para quem assina o link: sugere ao calendário buscar novidades a cada 6 horas.
        'REFRESH-INTERVAL;VALUE=DURATION:PT6H',
        'X-PUBLISHED-TTL:PT6H',
    ]
    carimbo = _ics_datetime(now())

    for escala in escalas:
        evento = escala.evento
        if not (evento and evento.data_inicio and evento.data_fim):
            continue
        equipe = escala.funcao.equipe.nome if escala.funcao and escala.funcao.equipe else ''
        funcao = escala.funcao.nome if escala.funcao else ''
        titulo = ' - '.join(p for p in (funcao, equipe) if p) or evento.nome
        situacao = 'Confirmada' if escala.confirmada else 'A confirmar'
        linhas += [
            'BEGIN:VEVENT',
            f'UID:escala-{escala.pk}@connect.simoesti.com.br',
            f'DTSTAMP:{carimbo}',
            f'DTSTART:{_ics_datetime(evento.data_inicio)}',
            f'DTEND:{_ics_datetime(evento.data_fim)}',
            f'SUMMARY:{_ics_escape(titulo)}',
            f'DESCRIPTION:{_ics_escape(f"{evento.nome} ({situacao})")}',
            'END:VEVENT',
        ]

    linhas.append('END:VCALENDAR')
    return '\r\n'.join(linhas) + '\r\n'


def resposta_ics(conteudo, nome_arquivo):
    response = HttpResponse(conteudo, content_type='text/calendar; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{nome_arquivo}"'
    return response


# ── Link sem sessão (app) ──

def _carimbo_da_senha(usuario):
    return usuario.get_session_auth_hash()[:16]


def token_da_agenda(usuario):
    return signing.dumps({'u': usuario.pk, 'h': _carimbo_da_senha(usuario)}, salt=SALT_AGENDA, compress=True)


def usuario_do_token(token):
    """Usuário dono do token, ou None se o token for inválido ou a senha tiver mudado."""
    try:
        dados = signing.loads(token, salt=SALT_AGENDA)
    except signing.BadSignature:
        return None
    usuario = get_user_model().objects.filter(pk=dados.get('u'), is_active=True).first()
    if usuario is None or not constant_time_compare(dados.get('h', ''), _carimbo_da_senha(usuario)):
        return None
    return usuario


def links_da_agenda(usuario):
    """URL https (baixar/importar) e webcal (assinar no calendário) das escalas do usuário."""
    https = settings.SITE_URL + reverse('agenda_ics', args=[token_da_agenda(usuario)])
    return {'https': https, 'webcal': 'webcal://' + https.split('://', 1)[1]}
