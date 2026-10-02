from datetime import datetime, time, timedelta

from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from evento.services import feed_calendario

from ..serializers.evento import EventoSerializer, JanelaCalendarioSerializer


def _inicio_do_dia(data):
    return timezone.make_aware(datetime.combine(data, time.min))


class EventoListView(APIView):
    """Calendário: eventos visíveis ao usuário na janela, com as escalas dele em cada um."""

    def get(self, request):
        params = JanelaCalendarioSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        dados = params.validated_data
        hoje = timezone.localdate()
        inicio = dados.get('inicio') or hoje - timedelta(days=30)
        fim = dados.get('fim') or hoje + timedelta(days=120)

        eventos = feed_calendario(
            request.user,
            filtro=dados.get('filtro', ''),
            equipe=dados.get('equipe', ''),
            inicio=_inicio_do_dia(inicio),
            fim=_inicio_do_dia(fim + timedelta(days=1)),
        )
        return Response([
            {
                **EventoSerializer(evento).data,
                'escalado': bool(minha),
                'confirmada': bool(minha and minha['confirmada']),
                'funcoes': minha['funcoes'] if minha else [],
            }
            for evento, minha in eventos
        ])
