# escala/utils.py
from django.db.models import Q
from .models import Escala
from disponivel.models import Disponivel
from ocupado.models import Ocupado

def usuarios_disponiveis_para_evento(equipe, evento, excluir_escala_id=None):
    """
    Retorna lista de user_ids disponíveis para o intervalo do evento,
    considerando:
      - membros aprovados da equipe,
      - sem 'Ocupado' sobrepondo,
      - com 'Disponivel' cobrindo totalmente o intervalo,
      - não já escalados neste mesmo evento.
    """
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
