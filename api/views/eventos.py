from datetime import datetime, time, timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from escala.models import Escala
from evento.models import Evento
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


class EscalaDoEventoView(APIView):
    """Quem está (ou esteve) escalado num evento, por equipe. Vale para quem enxerga o evento no calendário."""

    def get(self, request, pk):
        evento = get_object_or_404(Evento.objects.visiveis_para(request.user).select_related('equipe'), pk=pk)
        escalas = (
            Escala.objects.filter(evento=evento)
            .select_related('funcao__equipe', 'usuario')
            .order_by('funcao__equipe__nome', 'funcao__nome', 'pk')
        )
        equipes = {}
        for e in escalas:
            equipe = e.funcao.equipe.nome if e.funcao and e.funcao.equipe else 'Sem equipe'
            equipes.setdefault(equipe, []).append({
                'funcao': e.funcao.nome if e.funcao else '',
                'nome': (e.usuario.get_full_name() or e.usuario.username) if e.usuario else None,
                'confirmada': e.confirmada,
                'eu': e.usuario_id == request.user.pk,
            })
        return Response({
            'evento': EventoSerializer(evento).data,
            'passado': evento.data_fim < timezone.now(),
            # Pessoas antes das vagas em cada equipe.
            'equipes': [
                {'equipe': nome, 'pessoas': sorted(pessoas, key=lambda p: p['nome'] is None)}
                for nome, pessoas in equipes.items()
            ],
        })
