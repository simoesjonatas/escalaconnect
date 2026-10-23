from django.utils import timezone
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Aviso

LIMITE = 100


class AvisoSerializer(serializers.ModelSerializer):
    lido = serializers.SerializerMethodField()

    class Meta:
        model = Aviso
        fields = ['id', 'titulo', 'corpo', 'tipo', 'escala_id', 'criado_em', 'lido']

    def get_lido(self, aviso):
        return aviso.lido_em is not None


def nao_lidos(usuario):
    return Aviso.objects.filter(usuario=usuario, lido_em__isnull=True).count()


class AvisoListView(APIView):
    """Caixa de avisos do app: as notificações recebidas, das mais novas para as mais antigas."""

    def get(self, request):
        avisos = Aviso.objects.filter(usuario=request.user)[:LIMITE]
        return Response({'nao_lidos': nao_lidos(request.user), 'avisos': AvisoSerializer(avisos, many=True).data})


class LerAvisosView(APIView):
    """Marca todos os avisos como lidos (o app chama ao abrir a caixa)."""

    def post(self, request):
        Aviso.objects.filter(usuario=request.user, lido_em__isnull=True).update(lido_em=timezone.now())
        return Response({'nao_lidos': 0})
