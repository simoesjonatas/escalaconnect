# escala/utils.py
import random
from collections import defaultdict
from datetime import timedelta

from django.conf import settings
from django.db.models import Q, Count
from django.apps import apps
from django.utils.timezone import now, localtime

# Teto de escalas por voluntário dentro de um mesmo mês. Quem já atingiu esse
# número não é mais escalado naquele mês, mesmo que continue disponível — evita
# que alguém com muita disponibilidade e pouca carga acabe servindo o mês todo.
# Pode ser sobrescrito em settings (ESCALA_LIMITE_POR_MES).
LIMITE_ESCALAS_POR_MES = 2

def usuarios_disponiveis_para_evento(equipe, evento, excluir_escala_id=None):
    """
    Retorna lista de user_ids disponíveis para o intervalo do evento,
    considerando:
      - membros aprovados da equipe,
      - sem 'Ocupado' sobrepondo,
      - com 'Disponivel' cobrindo totalmente o intervalo,
      - não já escalados neste mesmo evento.
    """

    """
    Retorna lista de user_ids disponíveis para o intervalo do evento.
    Evita import circular resolvendo os modelos via apps.get_model.
    """
    Ocupado    = apps.get_model('ocupado', 'Ocupado')
    Disponivel = apps.get_model('disponivel', 'Disponivel')
    Escala     = apps.get_model('escala', 'Escala')
    # Membros aprovados da equipe
    membros_aprovados = equipe.membros.filter(aprovado=True).select_related('usuario')
    membro_user_ids = list(membros_aprovados.values_list('usuario_id', flat=True))

    if not membro_user_ids:
        return []

    # Remover quem está OCUPADO em qualquer parte do intervalo
    ocupados_ids = list(
        Ocupado.objects
        .filter(
            usuario_id__in=membro_user_ids,
            data_inicio__lt=evento.data_fim,
            data_fim__gt=evento.data_inicio
        )
        .values_list('usuario_id', flat=True)
        .distinct()
    )
    candidatos_ids = set(membro_user_ids) - set(ocupados_ids)
    if not candidatos_ids:
        return []

    # Manter apenas quem está DISPONÍVEL cobrindo TODO o intervalo do evento
    disponiveis_ids = list(
        Disponivel.objects
        .filter(
            usuario_id__in=candidatos_ids,
            data_inicio__lte=evento.data_inicio,
            data_fim__gte=evento.data_fim
        )
        .values_list('usuario_id', flat=True)
        .distinct()
    )
    if not disponiveis_ids:
        return []

    # Remover quem JÁ foi escalado neste evento (em qualquer função)
    escalados_ids = list(
        Escala.objects
        .filter(
            evento=evento,
            usuario_id__in=disponiveis_ids
        )
        .exclude(pk=excluir_escala_id)
        .values_list('usuario_id', flat=True)
        .distinct()
    )

    finais_ids = set(disponiveis_ids) - set(escalados_ids)
    return list(finais_ids)


def _ano_mes_local(dt):
    """(ano, mês) de um datetime no fuso local.

    Alinha com os lookups ``__year``/``__month`` do banco, que usam
    settings.TIME_ZONE quando USE_TZ=True — evita jogar um culto do fim do mês
    (ex.: sábado 23h) no mês errado por causa da diferença para UTC.
    """
    local = localtime(dt)
    return (local.year, local.month)


def preencher_vagas(escalas_vazias, limite_por_mes=None):
    """Atribui voluntários disponíveis às escalas vazias informadas.

    Critérios de escolha, em ordem:
      1. Teto mensal: quem já atingiu ``limite_por_mes`` escalas no mês daquele
         evento fica de fora, mesmo tendo disponibilidade (evita que alguém
         com muita disponibilidade e pouca carga sirva o mês inteiro).
      2. Escassez de disponibilidade: prioriza quem se colocou disponível menos
         vezes no mês — assim quem só marcou um dia é alocado justamente nele,
         em vez de perder a vaga para quem marcou o mês todo.
      3. Rodízio justo: por fim, prioriza quem serviu menos nos últimos 60 dias
         (desempate aleatório).

    Salva cada atribuição na hora — então a checagem de "já escalado no evento"
    (e o teto mensal) continua correta mesmo com várias vagas do mesmo evento e
    do mesmo mês. Não confirma presença (isso continua sendo ação do voluntário).
    Retorna quantas vagas foram preenchidas.
    """
    Escala = apps.get_model('escala', 'Escala')
    Disponivel = apps.get_model('disponivel', 'Disponivel')

    if limite_por_mes is None:
        limite_por_mes = getattr(settings, 'ESCALA_LIMITE_POR_MES', LIMITE_ESCALAS_POR_MES)

    # Rodízio justo (critério 3): carga histórica dos últimos 60 dias.
    desde = now() - timedelta(days=60)
    carga = dict(
        Escala.objects
        .filter(usuario__isnull=False, evento__data_inicio__gte=desde)
        .values('usuario_id')
        .annotate(total=Count('id'))
        .values_list('usuario_id', 'total')
    )

    # Meses (ano, mês) envolvidos nas vagas — as vagas podem cobrir vários meses
    # (auto-escala da equipe), e teto e prioridade são contados por mês.
    meses = {
        _ano_mes_local(e.evento.data_inicio)
        for e in escalas_vazias
        if e.evento and e.evento.data_inicio
    }

    # Critério 1: quantas escalas cada voluntário já tem em cada mês.
    escalas_no_mes = defaultdict(dict)
    # Critério 2: quantas disponibilidades cada voluntário cadastrou em cada mês.
    disp_no_mes = defaultdict(dict)
    for ano, mes in meses:
        escalas_no_mes[(ano, mes)] = dict(
            Escala.objects
            .filter(usuario__isnull=False,
                    evento__data_inicio__year=ano,
                    evento__data_inicio__month=mes)
            .values('usuario_id')
            .annotate(total=Count('id'))
            .values_list('usuario_id', 'total')
        )
        disp_no_mes[(ano, mes)] = dict(
            Disponivel.objects
            .filter(data_inicio__year=ano, data_inicio__month=mes)
            .values('usuario_id')
            .annotate(total=Count('id'))
            .values_list('usuario_id', 'total')
        )

    preenchidas = 0
    for escala in escalas_vazias:
        equipe = escala.funcao.equipe if escala.funcao else None
        if not (equipe and escala.evento and escala.evento.data_inicio):
            continue
        mkey = _ano_mes_local(escala.evento.data_inicio)

        ids = usuarios_disponiveis_para_evento(
            equipe=equipe, evento=escala.evento, excluir_escala_id=escala.pk
        )
        if not ids:
            continue

        # Critério 1 (teto mensal): descarta quem já bateu o limite no mês.
        elegiveis = [
            uid for uid in ids
            if escalas_no_mes[mkey].get(uid, 0) < limite_por_mes
        ]
        if not elegiveis:
            continue

        # Critério 2 (menos disponibilidade no mês) e 3 (menor carga; desempate
        # aleatório). Todo candidato tem ao menos 1 disponibilidade cobrindo o
        # evento, logo >= 1 no mês.
        escolhido = min(
            elegiveis,
            key=lambda uid: (
                disp_no_mes[mkey].get(uid, 0),
                carga.get(uid, 0),
                random.random(),
            ),
        )
        escala.usuario_id = escolhido
        escala.save(update_fields=['usuario'])
        carga[escolhido] = carga.get(escolhido, 0) + 1
        escalas_no_mes[mkey][escolhido] = escalas_no_mes[mkey].get(escolhido, 0) + 1
        preenchidas += 1
    return preenchidas
