from django.contrib.auth import get_user_model

from escalaconnect.periodos import Periodos
from ocupado.models import Ocupado

from .models import Disponivel

disponibilidades = Periodos(
    Disponivel, Ocupado,
    "Existe uma indisponibilidade registrada que conflita com este período de disponibilidade.",
    exige_equipe=True,
)


def membros_sem_disponibilidade(equipe, ano, mes):
    """Membros aprovados da equipe sem nenhuma disponibilidade no mês (mesmo critério do pedido por e-mail/app)."""
    from escalaconnect.tasks_availability import _month_bounds

    inicio, fim, _, _ = _month_bounds(ano, mes)
    com_disponibilidade = Disponivel.objects.filter(data_inicio__lte=fim, data_fim__gte=inicio).values('usuario_id')
    return (
        get_user_model().objects
        .filter(is_active=True, membrosequipe__equipe=equipe, membrosequipe__aprovado=True)
        .exclude(pk__in=com_disponibilidade)
        .order_by('first_name', 'username')
    )
