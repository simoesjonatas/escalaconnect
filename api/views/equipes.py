from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from equipe import services
from equipe.models import Equipe

from ..serializers.equipe import EquipeSerializer


def _equipes(usuario):
    aprovadas, pendentes = services.equipes_do_usuario(usuario)
    return Response({
        'aprovadas': EquipeSerializer(aprovadas, many=True).data,
        'pendentes': EquipeSerializer(pendentes, many=True).data,
        'disponiveis': EquipeSerializer(services.equipes_disponiveis(usuario), many=True).data,
    })


class EquipeListView(APIView):
    """Equipes do usuário (aprovadas e pendentes) e as que ele ainda pode pedir para entrar."""

    def get(self, request):
        return _equipes(request.user)


class CandidaturaView(APIView):
    """POST pede para entrar na equipe (o líder aprova pelo site); DELETE cancela o pedido pendente."""

    def post(self, request, pk):
        services.candidatar(request.user, get_object_or_404(Equipe, pk=pk))
        return _equipes(request.user)

    def delete(self, request, pk):
        services.cancelar_candidatura(request.user, get_object_or_404(Equipe, pk=pk))
        return _equipes(request.user)
