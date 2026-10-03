from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Device
from ..serializers.device import DeviceSerializer


class DeviceView(APIView):
    """Registra o aparelho para receber push. Liberado mesmo com senha/termo pendentes."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DeviceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dados = dict(serializer.validated_data)
        # O token identifica o aparelho: se outra pessoa entrar nele, o aparelho passa a ser dela.
        Device.objects.update_or_create(
            expo_token=dados.pop('expo_token'),
            defaults={**dados, 'usuario': request.user, 'ativo': True},
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class DeviceDetailView(APIView):
    """Para de enviar push a este aparelho (chamado pelo app antes do logout)."""
    permission_classes = [IsAuthenticated]

    def delete(self, request, token):
        Device.objects.filter(usuario=request.user, expo_token=token).update(ativo=False)
        return Response(status=status.HTTP_204_NO_CONTENT)
