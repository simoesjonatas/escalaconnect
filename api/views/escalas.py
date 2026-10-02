from django.db.models import Exists, OuterRef
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from escala import services
from escala.models import Desistencia, Escala, SolicitacaoTroca
from escalaconnect.services import pendencias_home

from ..serializers.escala import EscalaSerializer, ImpedimentoSerializer


def escalas_do_usuario(usuario, base=None):
    """Escalas do usuário com o que o EscalaSerializer precisa, sem consulta por item."""
    qs = base if base is not None else Escala.objects.filter(usuario=usuario)
    return qs.select_related('evento', 'funcao__equipe').annotate(
        # Mesmo critério de Escala.has_impedimento / has_solicitacao_troca_aberta.
        tem_impedimento=Exists(Desistencia.objects.filter(escala=OuterRef('pk'), aprovada=False)),
        troca_pendente=Exists(SolicitacaoTroca.objects.filter(escala_origem=OuterRef('pk'), aprovada=False)),
    )


def escalas_futuras(usuario):
    return escalas_do_usuario(usuario, services.escalas_futuras(usuario)).order_by('evento__data_inicio')


class EscalaDoUsuarioView(APIView):
    """Base das rotas /escalas/{id}/...: escala de outro usuário é 404."""

    def get_escala(self, pk):
        return get_object_or_404(escalas_do_usuario(self.request.user), pk=pk)

    def executar(self, servico, *args):
        """Roda um serviço de escala.services e devolve a escala atualizada."""
        escala = self.get_escala(self.kwargs['pk'])
        servico(escala, self.request.user, *args)  # RegraDeNegocio vira 400 no handler
        return Response(EscalaSerializer(self.get_escala(escala.pk)).data)


class HomeView(APIView):
    """Pendências do voluntário e a próxima escala, para a tela inicial."""

    def get(self, request):
        proxima = escalas_futuras(request.user).first()
        return Response({
            **pendencias_home(request.user),
            'proxima_escala': EscalaSerializer(proxima).data if proxima else None,
        })


class EscalaListView(APIView):
    def get(self, request):
        return Response(EscalaSerializer(escalas_futuras(request.user), many=True).data)


class EscalaDetailView(EscalaDoUsuarioView):
    def get(self, request, pk):
        return Response(EscalaSerializer(self.get_escala(pk)).data)


class ConfirmarEscalaView(EscalaDoUsuarioView):
    def post(self, request, pk):
        return self.executar(services.confirmar_escala)


class ImpedimentoView(EscalaDoUsuarioView):
    """Sinaliza impedimento (desistência com motivo), que o líder aprova pelo site."""

    def post(self, request, pk):
        serializer = ImpedimentoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self.executar(services.sinalizar_impedimento, serializer.validated_data['motivo'])


class TrocaView(EscalaDoUsuarioView):
    """POST pede a troca da escala; DELETE cancela o pedido pendente."""

    def post(self, request, pk):
        return self.executar(services.solicitar_troca)

    def delete(self, request, pk):
        return self.executar(services.cancelar_troca)
