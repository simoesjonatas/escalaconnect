from datetime import datetime

from django.db.models import Count, Exists, Min, OuterRef
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from escala import services
from escala.models import Desistencia, Escala, SolicitacaoTroca
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
            'vagas_abertas': sum(not v.me_ofereci for v in services.vagas_visiveis_para(request.user)),
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


class ColegasView(EscalaDoUsuarioView):
    """Quem serve com o voluntário no mesmo culto e na mesma equipe; função sem ninguém vem com nome nulo."""

    def get(self, request, pk):
        escala = self.get_escala(pk)
        outras = (
            Escala.objects
            .filter(evento_id=escala.evento_id, funcao__equipe_id=escala.funcao.equipe_id)
            .exclude(pk=escala.pk)
            .select_related('funcao', 'usuario')
        )
        outras = sorted(outras, key=lambda e: (e.usuario_id is None, e.funcao.nome))  # pessoas antes das vagas
        return Response([
            {
                'funcao': e.funcao.nome,
                'nome': (e.usuario.get_full_name() or e.usuario.username) if e.usuario else None,
                'confirmada': e.confirmada,
            }
            for e in outras
        ])


ULTIMAS_DO_HISTORICO = 10


class HistoricoView(APIView):
    """Quantas vezes o voluntário já serviu (cultos que já começaram), por função, e as últimas escalas."""

    def get(self, request):
        agora = timezone.now()
        hoje = timezone.localdate(agora)
        inicio_mes = timezone.make_aware(datetime(hoje.year, hoje.month, 1))
        inicio_ano = timezone.make_aware(datetime(hoje.year, 1, 1))
        servidas = Escala.objects.filter(usuario=request.user, evento__data_inicio__lte=agora)
        por_funcao = (
            servidas.values('funcao__nome', 'funcao__equipe__nome')
            .annotate(total=Count('id'))
            .order_by('-total', 'funcao__nome')
        )
        return Response({
            'mes': servidas.filter(evento__data_inicio__gte=inicio_mes).count(),
            'ano': servidas.filter(evento__data_inicio__gte=inicio_ano).count(),
            'total': servidas.count(),
            'desde': servidas.aggregate(desde=Min('evento__data_inicio'))['desde'],
            'por_funcao': [
                {'funcao': f['funcao__nome'], 'equipe': f['funcao__equipe__nome'], 'total': f['total']}
                for f in por_funcao
            ],
            'ultimas': EscalaSerializer(
                escalas_do_usuario(request.user, servidas).order_by('-evento__data_inicio')[:ULTIMAS_DO_HISTORICO],
                many=True).data,
        })


class VagaAbertaListView(APIView):
    """Vagas em aberto das equipes do voluntário (até alguém ser escalado), para ele se oferecer."""

    def get(self, request):
        return Response(VagaAbertaSerializer(services.vagas_visiveis_para(request.user), many=True).data)


class OfertaView(APIView):
    """POST: oferece-se para a vaga (o líder aprova no app ou no site). DELETE: desiste da oferta."""

    def responder(self, pk):
        vaga = next((v for v in services.vagas_visiveis_para(self.request.user) if v.pk == pk), None)
        return Response(VagaAbertaSerializer(vaga).data if vaga else None)

    def post(self, request, pk):
        services.oferecer_para_vaga(get_object_or_404(Escala, pk=pk), request.user)
        return self.responder(pk)

    def delete(self, request, pk):
        services.cancelar_oferta(get_object_or_404(Escala, pk=pk), request.user)
        return self.responder(pk)
