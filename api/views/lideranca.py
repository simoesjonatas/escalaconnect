"""Painel do líder no app: pendências (aprovar/recusar) e vagas em aberto.

Tudo restrito às equipes que o usuário lidera (todas, para staff); item de outra
equipe é 404. As regras são as mesmas do site (escala.services, equipe.services).
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from equipe import services as equipe_services
from equipe.models import MembrosEquipe
from escala import services as escala_services
from escala.models import Desistencia, Escala, SolicitacaoTroca
from escala.utils import _ano_mes_local, usuarios_disponiveis_para_evento

from ..serializers.lideranca import (
    CandidatoSerializer, CandidaturaSerializer, EscalarSerializer, ImpedimentoSerializer,
    TrocaSerializer, VagaSerializer,
)

DIAS_DE_VAGAS = 60


def pode_liderar(usuario):
    return usuario.is_staff or usuario.is_superuser or usuario.is_leader()


class Lider(BasePermission):
    message = 'Disponível só para a liderança das equipes.'

    def has_permission(self, request, view):
        return pode_liderar(request.user)


class LiderView(APIView):
    permission_classes = [*APIView.permission_classes, Lider]

    def equipes(self):
        return equipe_services.equipes_lideradas(self.request.user)


class PendenciasView(LiderView):
    def get(self, request):
        pendencias = equipe_services.pendencias_do_lider(request.user)
        return Response({
            'impedimentos': ImpedimentoSerializer(pendencias['impedimentos'], many=True).data,
            'trocas': TrocaSerializer(pendencias['trocas'], many=True).data,
            'candidaturas': CandidaturaSerializer(pendencias['candidaturas'], many=True).data,
        })


class ImpedimentoView(LiderView):
    def post(self, request, pk, acao):
        desistencia = get_object_or_404(
            Desistencia.objects.select_related('escala__evento', 'escala__funcao'),
            pk=pk, aprovada=False, escala__funcao__equipe__in=self.equipes(),
        )
        if acao == 'aprovar':
            escala_services.aprovar_desistencia(desistencia)
            return Response({'vaga_id': desistencia.escala_id})  # o app oferece escalar alguém na vaga
        escala_services.recusar_desistencia(desistencia)
        return Response(status=204)


class TrocaView(LiderView):
    def post(self, request, pk, acao):
        troca = get_object_or_404(
            SolicitacaoTroca.objects.select_related('escala_origem__evento', 'escala_origem__funcao'),
            pk=pk, aprovada=False, escala_origem__funcao__equipe__in=self.equipes(),
        )
        if acao == 'aprovar':
            escala_services.aprovar_troca(troca, request.user)
            return Response({'vaga_id': troca.escala_origem_id})
        escala_services.recusar_troca(troca)
        return Response(status=204)


class CandidaturaView(LiderView):
    def post(self, request, pk, acao):
        membro = get_object_or_404(
            MembrosEquipe.objects.select_related('equipe'), pk=pk, aprovado=False, equipe__in=self.equipes())
        if acao == 'aprovar':
            equipe_services.aprovar_candidatura(membro)
        else:
            equipe_services.recusar_candidatura(membro)
        return Response(status=204)


def _vagas(equipes):
    agora = timezone.now()
    return (
        Escala.objects
        .filter(usuario__isnull=True, funcao__equipe__in=equipes,
                evento__data_inicio__gt=agora, evento__data_inicio__lte=agora + timedelta(days=DIAS_DE_VAGAS))
        .select_related('evento', 'funcao__equipe')
        .order_by('evento__data_inicio', 'funcao__equipe__nome', 'funcao__nome')
    )


class VagaListView(LiderView):
    """Vagas em aberto nos próximos 60 dias, com quantos membros estão disponíveis em cada uma."""

    def get(self, request):
        vagas = list(_vagas(self.equipes()))
        for vaga in vagas:
            vaga.disponiveis = len(usuarios_disponiveis_para_evento(vaga.equipe, vaga.evento, excluir_escala_id=vaga.pk))
        return Response(VagaSerializer(vagas, many=True).data)


class VagaDetailView(LiderView):
    """Uma vaga e os membros aprovados da equipe que podem ocupá-la, disponíveis primeiro."""

    def get_vaga(self, pk):
        return get_object_or_404(_vagas(self.equipes()), pk=pk)

    def get(self, request, pk):
        vaga = self.get_vaga(pk)
        disponiveis = set(usuarios_disponiveis_para_evento(vaga.equipe, vaga.evento, excluir_escala_id=vaga.pk))
        ja_no_evento = Escala.objects.filter(evento=vaga.evento, usuario__isnull=False).values('usuario_id')
        membros = (
            get_user_model().objects
            .filter(membrosequipe__equipe=vaga.equipe, membrosequipe__aprovado=True, is_active=True)
            .exclude(pk__in=ja_no_evento)
        )
        ano, mes = _ano_mes_local(vaga.evento.data_inicio)
        servicos = dict(
            Escala.objects
            .filter(usuario__in=membros, evento__data_inicio__year=ano, evento__data_inicio__month=mes)
            .values('usuario_id').annotate(total=Count('id')).values_list('usuario_id', 'total')
        )
        candidatos = []
        for membro in membros:
            membro.disponivel = membro.pk in disponiveis
            membro.servicos_no_mes = servicos.get(membro.pk, 0)
            candidatos.append(membro)
        # Disponíveis primeiro; depois quem serviu menos no mês; depois por nome.
        candidatos.sort(key=lambda m: (not m.disponivel, m.servicos_no_mes, (m.get_full_name() or m.username).lower()))
        return Response({
            'vaga': {**VagaSerializer(vaga).data, 'disponiveis': len(disponiveis)},
            'candidatos': CandidatoSerializer(candidatos, many=True).data,
        })


class EscalarView(VagaDetailView):
    http_method_names = ['post', 'options']

    def post(self, request, pk):
        """Escala o membro escolhido na vaga; ele recebe o push "Você foi escalado"."""
        vaga = self.get_vaga(pk)
        dados = EscalarSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        usuario = get_object_or_404(get_user_model(), pk=dados.validated_data['usuario_id'], is_active=True)
        escala_services.escalar_em_vaga(vaga, usuario)
        return Response(status=204)
