# escala/utils.py
import random
from datetime import timedelta

from django.db.models import Q, Count
from django.apps import apps
from django.utils.timezone import now

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


def preencher_vagas(escalas_vazias):
    """Atribui voluntários disponíveis às escalas vazias informadas.

    Prioriza quem serviu menos nos últimos 60 dias (rodízio justo) e salva cada
    atribuição na hora — então a checagem de "já escalado no evento" continua
    correta mesmo quando há várias vagas do mesmo evento. Não confirma presença
    (isso continua sendo ação do voluntário). Retorna quantas vagas foram preenchidas.
    """
    Escala = apps.get_model('escala', 'Escala')

    desde = now() - timedelta(days=60)
    carga = dict(
        Escala.objects
        .filter(usuario__isnull=False, evento__data_inicio__gte=desde)
        .values('usuario_id')
        .annotate(total=Count('id'))
        .values_list('usuario_id', 'total')
    )

    preenchidas = 0
    for escala in escalas_vazias:
        equipe = escala.funcao.equipe if escala.funcao else None
        if not (equipe and escala.evento):
            continue
        ids = usuarios_disponiveis_para_evento(
            equipe=equipe, evento=escala.evento, excluir_escala_id=escala.pk
        )
        if not ids:
            continue
        # Menos sobrecarregado primeiro; desempate aleatório.
        escolhido = min(ids, key=lambda uid: (carga.get(uid, 0), random.random()))
        escala.usuario_id = escolhido
        escala.save(update_fields=['usuario'])
        carga[escolhido] = carga.get(escolhido, 0) + 1
        preenchidas += 1
    return preenchidas
