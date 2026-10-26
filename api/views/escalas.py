from django.db.models import Exists, OuterRef
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from escala import services
from escala.models import Desistencia, Escala, Rendimento, SolicitacaoTroca
from equipe.services import total_pendencias_do_lider
from escalaconnect.services import pendencias_home

from .avisos import nao_lidos
from .lideranca import pode_liderar
from ..serializers.escala import EscalaSerializer, ImpedimentoSerializer
from ..serializers.lideranca import VagaAbertaSerializer


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


def vagas_abertas(usuario):
    """Vagas das equipes do usuário, marcando as em que ele já se ofereceu."""
    return (
        services.vagas_abertas_para(usuario)
        .select_related('evento', 'funcao__equipe')
        .annotate(me_ofereci=Exists(Rendimento.objects.filter(escala=OuterRef('pk'), candidato=usuario, aprovada=False)))
        .order_by('evento__data_inicio', 'funcao__equipe__nome', 'funcao__nome')
    )


def vagas_para_mostrar(usuario):
    """Vagas que o voluntário vê: onde ninguém da equipe está disponível, mais as que ele já se ofereceu."""
    vagas = list(vagas_abertas(usuario))
    sem_disponivel = {v.pk for v in services.sem_ninguem_disponivel([v for v in vagas if not v.me_ofereci])}
    return [v for v in vagas if v.me_ofereci or v.pk in sem_disponivel]


class HomeView(APIView):
    """Pendências do voluntário e a próxima escala, para a tela inicial."""

    def get(self, request):
        proxima = escalas_futuras(request.user).first()
        return Response({
            **pendencias_home(request.user),
            'proxima_escala': EscalaSerializer(proxima).data if proxima else None,
            # Sem equipe aprovada o app pede para entrar em uma antes de informar disponibilidade.
            'em_equipe': request.user.is_in_team(),
            'avisos_nao_lidos': nao_lidos(request.user),
            # Vagas da equipe em que o voluntário ainda pode se oferecer.
            'vagas_abertas': sum(not v.me_ofereci for v in vagas_para_mostrar(request.user)),
            'pendencias_lider': total_pendencias_do_lider(request.user) if pode_liderar(request.user) else 0,
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


class VagaAbertaListView(APIView):
    """Vagas em aberto das equipes do voluntário em que ninguém marcou disponibilidade, para ele se oferecer."""

    def get(self, request):
        return Response(VagaAbertaSerializer(vagas_para_mostrar(request.user), many=True).data)


class OfertaView(APIView):
    """POST: oferece-se para a vaga (o líder aprova no app ou no site). DELETE: desiste da oferta."""

    def responder(self, pk):
        vaga = vagas_abertas(self.request.user).filter(pk=pk).first()
        return Response(VagaAbertaSerializer(vaga).data if vaga else None)

    def post(self, request, pk):
        services.oferecer_para_vaga(get_object_or_404(Escala, pk=pk), request.user)
        return self.responder(pk)

    def delete(self, request, pk):
        services.cancelar_oferta(get_object_or_404(Escala, pk=pk), request.user)
        return self.responder(pk)
