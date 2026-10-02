from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..serializers.evento import EventoSerializer
from ..serializers.periodo import PeriodoSerializer, PorEventoSerializer


class PeriodosView(APIView):
    """Base das rotas de /disponibilidades/ e /indisponibilidades/.

    `periodos` é a instância de escalaconnect.periodos.Periodos, definida em
    api/urls.py: as regras são as mesmas para os dois lados.
    """
    periodos = None

    def get_periodo(self, pk):
        # Registro de outro usuário é 404.
        return get_object_or_404(self.periodos.do_usuario(self.request.user).select_related('evento'), pk=pk)


class PeriodoListView(PeriodosView):
    def get(self, request):
        qs = self.periodos.futuros(request.user).select_related('evento').order_by('data_inicio')
        return Response(PeriodoSerializer(qs, many=True).data)

    def post(self, request):
        serializer = PeriodoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dados = serializer.validated_data
        self.periodos.validar(request.user, dados['data_inicio'], dados['data_fim'])
        periodo = self.periodos.modelo.objects.create(usuario=request.user, **dados)
        return Response(PeriodoSerializer(periodo).data, status=status.HTTP_201_CREATED)


class PeriodoDetailView(PeriodosView):
    def patch(self, request, pk):
        periodo = self.get_periodo(pk)
        serializer = PeriodoSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        for campo, valor in serializer.validated_data.items():
            setattr(periodo, campo, valor)
        self.periodos.validar(request.user, periodo.data_inicio, periodo.data_fim)
        periodo.save()
        return Response(PeriodoSerializer(periodo).data)

    def delete(self, request, pk):
        self.get_periodo(pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PeriodoEventosView(PeriodosView):
    """Eventos dos próximos 60 dias em que o usuário ainda não registrou este tipo de período."""

    def get(self, request):
        eventos = self.periodos.eventos_elegiveis(request.user).select_related('equipe')
        return Response(EventoSerializer(eventos, many=True).data)


class PeriodoPorEventoView(PeriodosView):
    """Registra um período para cada evento escolhido."""

    def post(self, request):
        serializer = PorEventoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        criados = self.periodos.registrar_por_eventos(request.user, serializer.validated_data['evento_ids'])
        return Response({'criados': criados})
