"""Painel do líder no app: pendências (aprovar/recusar), vagas em aberto, cultos e
pedido de disponibilidade.

Tudo restrito às equipes que o usuário lidera (todas, para staff); item de outra
equipe é 404. As regras são as mesmas do site (escala.services, equipe.services).
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, Exists, OuterRef, Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from equipe import services as equipe_services
from equipe.models import MembrosEquipe
from escala import services as escala_services
from disponivel.services import membros_sem_disponibilidade
from escala.models import Desistencia, Escala, Rendimento, SolicitacaoTroca
from escala.services import DIAS_DE_VAGAS
from escala.utils import _ano_mes_local, usuarios_disponiveis_para_evento
from escalaconnect.notificacoes import pedir_confirmacao
from escalaconnect.tasks_availability import disparar_pedido_disponibilidades
from evento.models import Evento

from ..serializers.equipe import EquipeSerializer
from ..serializers.evento import EventoSerializer
from ..serializers.lideranca import (
    CandidatoSerializer, CandidaturaSerializer, EscalaDoCultoSerializer, EscalarSerializer, ImpedimentoSerializer,
    OfertaSerializer, PedirDisponibilidadeSerializer, PessoaSerializer, TrocaSerializer, VagaSerializer,
)


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
            'ofertas': OfertaSerializer(pendencias['ofertas'], many=True).data,
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


class OfertaView(LiderView):
    """Aprovar escala quem se ofereceu para a vaga; recusar descarta a oferta e avisa a pessoa."""

    def post(self, request, pk, acao):
        oferta = get_object_or_404(
            escala_services.ofertas_pendentes().select_related('escala__evento', 'escala__funcao', 'candidato'),
            pk=pk, escala__funcao__equipe__in=self.equipes(),
        )
        if acao == 'aprovar':
            escala_services.aprovar_oferta(oferta)
        else:
            escala_services.recusar_oferta(oferta)
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
        # Quantas pessoas se ofereceram para a vaga e ainda esperam a decisão do líder.
        .annotate(ofertas=Count('rendimento', filter=Q(rendimento__aprovada=False)))
        .order_by('evento__data_inicio', 'funcao__equipe__nome', 'funcao__nome')
    )


class VagaListView(LiderView):
    """Vagas em aberto nos próximos 60 dias, com quantos se ofereceram e quantos estão disponíveis."""

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
        ofereceram = set(
            Rendimento.objects.filter(escala=vaga, aprovada=False).values_list('candidato_id', flat=True))
        candidatos = []
        for membro in membros:
            membro.disponivel = membro.pk in disponiveis
            membro.se_ofereceu = membro.pk in ofereceram
            membro.servicos_no_mes = servicos.get(membro.pk, 0)
            candidatos.append(membro)
        # Quem se ofereceu, depois disponíveis; depois quem serviu menos no mês; depois por nome.
        candidatos.sort(key=lambda m: (
            not m.se_ofereceu, not m.disponivel, m.servicos_no_mes, (m.get_full_name() or m.username).lower()))
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


# ── Cultos: quem confirmou, quem falta e vagas ──

def _escalas_dos_cultos(equipes):
    agora = timezone.now()
    return Escala.objects.filter(
        funcao__equipe__in=equipes,
        evento__data_fim__gt=agora, evento__data_inicio__lte=agora + timedelta(days=DIAS_DE_VAGAS),
    )


class CultoListView(LiderView):
    """Próximos eventos com escalas das equipes lideradas, com a contagem de cada situação.

    `por_equipe` traz as mesmas contagens separadas por equipe, para o filtro do app.
    """

    def get(self, request):
        por_evento = {}
        linhas = (
            _escalas_dos_cultos(self.equipes())
            .values('evento_id', 'funcao__equipe_id', 'funcao__equipe__nome')
            .annotate(
                total=Count('id'),
                vagas=Count('id', filter=Q(usuario__isnull=True)),
                confirmadas=Count('id', filter=Q(usuario__isnull=False, confirmada=True)),
            )
            .order_by('funcao__equipe__nome')
        )
        for linha in linhas:
            por_evento.setdefault(linha['evento_id'], []).append({
                'equipe_id': linha['funcao__equipe_id'],
                'equipe': linha['funcao__equipe__nome'],
                'total': linha['total'],
                'vagas': linha['vagas'],
                'confirmadas': linha['confirmadas'],
                'pendentes': linha['total'] - linha['vagas'] - linha['confirmadas'],
            })
        eventos = Evento.objects.filter(pk__in=por_evento).select_related('equipe').order_by('data_inicio')
        return Response([
            {
                **EventoSerializer(evento).data,
                **{campo: sum(e[campo] for e in por_evento[evento.pk])
                   for campo in ('total', 'vagas', 'confirmadas', 'pendentes')},
                'por_equipe': por_evento[evento.pk],
            }
            for evento in eventos
        ])


class CultoView(LiderView):
    def get_escalas(self, evento_id):
        escalas = (
            _escalas_dos_cultos(self.equipes()).filter(evento_id=evento_id)
            .select_related('evento__equipe', 'funcao__equipe', 'usuario')
            .annotate(
                tem_impedimento=Exists(Desistencia.objects.filter(escala=OuterRef('pk'), aprovada=False)),
                troca_pendente=Exists(SolicitacaoTroca.objects.filter(escala_origem=OuterRef('pk'), aprovada=False)),
            )
            .order_by('funcao__equipe__nome', 'funcao__nome', 'pk')
        )
        if not escalas:
            raise Http404
        return escalas


class CultoDetailView(CultoView):
    """Escalas das equipes lideradas num evento."""

    def get(self, request, pk):
        escalas = list(self.get_escalas(pk))
        vagas = [e for e in escalas if not e.usuario_id]
        ofertas = {}
        for oferta in (Rendimento.objects.filter(escala__in=vagas, aprovada=False)
                       .select_related('candidato').order_by('data_candidatura')):
            ofertas.setdefault(oferta.escala_id, []).append(oferta.candidato)
        for vaga in vagas:
            vaga.ofertas = ofertas.get(vaga.pk, [])
            vaga.disponiveis = len(usuarios_disponiveis_para_evento(vaga.equipe, vaga.evento, excluir_escala_id=vaga.pk))
        return Response({
            'evento': EventoSerializer(escalas[0].evento).data,
            'escalas': EscalaDoCultoSerializer(escalas, many=True).data,
        })


class PedirConfirmacaoView(CultoView):
    """Pede a confirmação (e-mail e app) só de quem ainda não confirmou, nas equipes lideradas."""

    def post(self, request, pk):
        escalas = self.get_escalas(pk)
        pendentes = [e for e in escalas if e.usuario_id and not e.confirmada]
        if not pendentes:
            return Response({'pendentes': 0})
        pedir_confirmacao(escalas[0].evento, equipes=self.equipes())
        return Response({'pendentes': len(pendentes)})


# ── Pedido de disponibilidade ──

def _proximo_mes():
    hoje = timezone.localdate()
    return (hoje.year + 1, 1) if hoje.month == 12 else (hoje.year, hoje.month + 1)


class DisponibilidadeDaEquipeView(LiderView):
    """Quem da equipe ainda não marcou disponibilidade no mês (padrão: próximo mês, primeira equipe)."""

    def get(self, request):
        equipes = list(self.equipes().order_by('nome'))
        if not equipes:
            return Response({'equipes': [], 'equipe_id': None, 'ano': None, 'mes': None, 'faltantes': [], 'membros': 0})
        try:
            equipe_id = int(request.query_params.get('equipe') or equipes[0].pk)
            ano, mes = _proximo_mes()
            ano = int(request.query_params.get('ano') or ano)
            mes = int(request.query_params.get('mes') or mes)
        except ValueError:
            raise ValidationError('Parâmetros inválidos.')
        if not 1 <= mes <= 12:
            raise ValidationError('Mês inválido.')
        equipe = next((e for e in equipes if e.pk == equipe_id), None)
        if equipe is None:
            raise Http404
        faltantes = membros_sem_disponibilidade(equipe, ano, mes)
        return Response({
            'equipes': EquipeSerializer(equipes, many=True).data,
            'equipe_id': equipe.pk,
            'ano': ano,
            'mes': mes,
            'faltantes': PessoaSerializer(faltantes, many=True).data,
            'membros': MembrosEquipe.objects.filter(equipe=equipe, aprovado=True, usuario__is_active=True).count(),
        })


class PedirDisponibilidadeView(LiderView):
    """Mesmo botão do site: pede a disponibilidade do mês a quem ainda não marcou (só app, ou e-mail e app)."""

    def post(self, request):
        dados = PedirDisponibilidadeSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        dados = dados.validated_data
        equipe = get_object_or_404(self.equipes(), pk=dados['equipe_id'])
        faltantes = membros_sem_disponibilidade(equipe, dados['ano'], dados['mes']).count()
        if faltantes:
            disparar_pedido_disponibilidades.delay(
                ano=dados['ano'], mes=dados['mes'], equipe_id=equipe.pk,
                lider_nome=request.user.get_full_name() or request.user.get_username(),
                canais=['push'] if dados['canal'] == 'app' else ['email', 'push'],
            )
        return Response({'faltantes': faltantes})
