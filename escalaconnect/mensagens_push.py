"""Textos das notificações push: título curto (o que aconteceu) e corpo (quando/onde).

Pensados para serem entendidos com a tela bloqueada. Quem já confirmou a escala
nunca recebe tom de cobrança; o "falta confirmar" aparece só para quem não confirmou.
Cada função devolve (titulo, corpo). O e-mail tem textos próprios e não usa este módulo.
"""
from datetime import timedelta

from django.utils import formats, timezone


def _hora(dt):
    return formats.date_format(timezone.localtime(dt), 'H:i')


def _dia(dt):
    """'hoje', 'amanhã' ou 'dom 25/10', no fuso local."""
    data = timezone.localtime(dt).date()
    hoje = timezone.localdate()
    if data == hoje:
        return 'hoje'
    if data == hoje + timedelta(days=1):
        return 'amanhã'
    return formats.date_format(data, 'D d/m').lower()


def _quando(dt):
    """'amanhã, 19:30' ou 'dom 25/10, 09:45'."""
    return f'{_dia(dt)}, {_hora(dt)}'


def _nome(usuario):
    return usuario.get_full_name() or usuario.username


def nome_da_equipe(nome):
    """'equipe Recepção', sem repetir quando o nome já começa com "Equipe"."""
    return nome if nome.lower().startswith('equipe') else f'equipe {nome}'


# ── Para o voluntário ──

def escalado(escala):
    evento = escala.evento
    return 'Você foi escalado 🙌', f'{evento.nome} · {_quando(evento.data_inicio)}'


def pedido_de_confirmacao(escala):
    evento = escala.evento
    return 'Confirma sua escala?', f'{evento.nome} · {_quando(evento.data_inicio)} · {escala.funcao.nome}'


def lembrete_da_escala(escala):
    """Lembrete da véspera ou do dia; o texto muda conforme a pessoa já confirmou ou não."""
    evento = escala.evento
    dia, hora = _dia(evento.data_inicio), _hora(evento.data_inicio)
    dia_titulo = dia.capitalize() if dia in ('hoje', 'amanhã') else f'No {dia}'
    if not escala.confirmada:
        return f'{dia_titulo} você serve às {hora}', f'{evento.nome} · toque para confirmar'
    if dia == 'amanhã':
        return 'Amanhã é dia de servir 💚', f'{evento.nome} · {hora} · {escala.funcao.nome}'
    return f'{dia_titulo} você serve às {hora} 💚', f'{evento.nome} · {escala.funcao.nome}'


def ultima_chamada(escala):
    """Poucas horas antes, só para quem ainda não confirmou."""
    evento = escala.evento
    return f'Sua escala começa às {_hora(evento.data_inicio)}', f'{evento.nome} · falta só confirmar sua presença'


def impedimento_aceito(escala):
    return 'Impedimento aceito', f'Você saiu da escala de {_dia(escala.evento.data_inicio)}. Obrigado por avisar!'


def troca_aprovada(escala):
    return 'Troca aprovada', f'Você saiu da escala de {_dia(escala.evento.data_inicio)}'


def pedido_recusado(escala):
    return 'Você continua escalado', f'A liderança não aprovou o pedido para {_dia(escala.evento.data_inicio)}'


def oferta_nao_aceita(escala):
    return 'Obrigado por se oferecer', f'A vaga de {_dia(escala.evento.data_inicio)} não ficou com você desta vez'


def entrada_na_equipe(equipe):
    return 'Boas-vindas à equipe! 🙌', f'Agora você faz parte da {nome_da_equipe(equipe.nome)}'


def pedido_de_disponibilidade(primeiro_dia_do_mes):
    mes = formats.date_format(primeiro_dia_do_mes, 'F').lower()
    return 'Quando você pode servir?', f'Marque seus dias de {mes}'


# ── Para o líder ──

def lider_impedimento(desistencia):
    escala = desistencia.escala
    return (
        'Impedimento na escala',
        f'{_nome(desistencia.usuario)} · {_quando(escala.evento.data_inicio)} · {escala.funcao.nome}',
    )


def lider_troca(troca):
    escala = troca.escala_origem
    return 'Pedido de troca', f'{_nome(troca.solicitante)} · {_quando(escala.evento.data_inicio)} · {escala.funcao.nome}'


def lider_candidatura(membro):
    return 'Nova candidatura', f'{_nome(membro.usuario)} quer entrar na {nome_da_equipe(membro.equipe.nome)}'


def lider_ofertas(evento, quantas):
    """Várias ofertas para o mesmo culto, num aviso só."""
    pessoas = '1 pessoa quer servir' if quantas == 1 else f'{quantas} pessoas querem servir'
    return pessoas, f'{evento.nome} · {_quando(evento.data_inicio)}'


def lider_oferta(oferta):
    escala = oferta.escala
    return (
        'Voluntário para a vaga',
        f'{_nome(oferta.candidato)} · {_quando(escala.evento.data_inicio)} · {escala.funcao.nome}',
    )
