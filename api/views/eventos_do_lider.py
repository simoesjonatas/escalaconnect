"""Ferramentas do líder no app: criar evento, gerar eventos em massa, adicionar funções a
eventos e exportar a escala em PDF.

Mesmas regras do site (evento.services e equipe.views_pdf): o líder só mexe nas equipes
que lidera; evento público (sem equipe) só o admin cria.
"""
from datetime import timedelta

from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import formats, timezone
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from equipe.views_pdf import link_do_pdf
from escala.models import Escala, Funcao
from evento import services as evento_services
from evento.models import Evento

from ..serializers.evento import EventoSerializer
from ..serializers.eventos_do_lider import (
    AplicarFuncoesSerializer, EventosEmMassaSerializer, NovoEventoSerializer, PdfDaEscalaSerializer,
)
from .lideranca import LiderView


def _meses_para_gerar():
    """Mês atual e o próximo ('AAAA-MM'), os mesmos que o "Gerar em Massa" do site oferece."""
    hoje = timezone.localdate()
    proximo = (hoje.replace(day=28) + timedelta(days=4)).replace(day=1)
    return [(d.strftime('%Y-%m'), formats.date_format(d, 'F/Y')) for d in (hoje, proximo)]


def _admin(usuario):
    return usuario.is_staff or usuario.is_superuser


class FerramentasView(LiderView):
    def equipe_escolhida(self, equipe_id):
        return get_object_or_404(self.equipes(), pk=equipe_id)

    def funcoes_da_equipe(self, equipe, funcao_ids):
        funcoes = list(Funcao.objects.filter(equipe=equipe, pk__in=funcao_ids))
        if len(funcoes) != len(funcao_ids):
            raise ValidationError({'funcao_ids': f'Escolha só funções da equipe {equipe.nome}.'})
        return funcoes

    def eventos_editaveis(self):
        """Eventos futuros em que o líder pode pôr funções: os da equipe dele e os públicos (cultos)."""
        eventos = Evento.objects.filter(data_fim__gte=timezone.now())
        if not _admin(self.request.user):
            eventos = eventos.filter(Q(equipe__isnull=True) | Q(equipe__in=self.equipes()))
        return eventos.select_related('equipe').order_by('data_inicio', 'nome')


class OpcoesView(FerramentasView):
    """O que as telas precisam: equipes lideradas com as funções, meses do "em massa" e se é admin."""

    def get(self, request):
        equipes = list(self.equipes().order_by('nome').prefetch_related('funcao_set'))
        return Response({
            'admin': _admin(request.user),
            'equipes': [
                {'id': e.pk, 'nome': e.nome,
                 'funcoes': [{'id': f.pk, 'nome': f.nome} for f in sorted(e.funcao_set.all(), key=lambda f: f.nome)]}
                for e in equipes
            ],
            'meses': [{'valor': valor, 'rotulo': rotulo} for valor, rotulo in _meses_para_gerar()],
        })


class EventosView(FerramentasView):
    def get(self, request):
        """Eventos futuros onde dá para adicionar funções, com as funções das equipes do líder já presentes."""
        eventos = list(self.eventos_editaveis()[:200])
        presentes = {}
        for evento_id, funcao_id in (Escala.objects
                                     .filter(evento__in=eventos, funcao__equipe__in=self.equipes())
                                     .values_list('evento_id', 'funcao_id')):
            presentes.setdefault(evento_id, set()).add(funcao_id)
        return Response([
            {**EventoSerializer(e).data, 'funcao_ids': sorted(presentes.get(e.pk, ()))} for e in eventos
        ])

    def post(self, request):
        """Cria um evento da equipe (ou público, se admin) com uma vaga por função escolhida."""
        dados = NovoEventoSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        dados = dados.validated_data
        if dados['equipe_id'] is None:
            if not _admin(request.user):
                raise ValidationError({'equipe_id': 'Escolha a equipe do evento.'})
            equipe, funcoes = None, list(Funcao.objects.filter(pk__in=dados['funcao_ids']))
        else:
            equipe = self.equipe_escolhida(dados['equipe_id'])
            funcoes = self.funcoes_da_equipe(equipe, dados['funcao_ids'])
        evento = evento_services.criar_evento(
            dados['nome'], equipe, dados['data_inicio'], dados['data_fim'], dados['observacao'], funcoes)
        return Response({**EventoSerializer(evento).data, 'vagas': len(funcoes)}, status=201)


class EventosEmMassaView(FerramentasView):
    def post(self, request):
        dados = EventosEmMassaSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        dados = dados.validated_data
        permitidos = {valor for valor, _ in _meses_para_gerar()}
        if not set(dados['meses']) <= permitidos:
            raise ValidationError({'meses': 'Escolha só o mês atual ou o próximo.'})
        equipe = self.equipe_escolhida(dados['equipe_id'])
        funcoes = self.funcoes_da_equipe(equipe, dados['funcao_ids'])
        eventos, ignorados = evento_services.gerar_eventos_em_massa(
            dados['nome'], equipe, sorted(dados['meses']), dados['dias_da_semana'],
            dados['horario_inicio'], dados['horario_fim'], dados['observacao'], funcoes)
        return Response({'criados': len(eventos), 'ignorados': ignorados, 'vagas_por_evento': len(funcoes)},
                        status=201)


class AplicarFuncoesView(FerramentasView):
    def post(self, request):
        """Adiciona as funções escolhidas (das equipes do líder) aos eventos escolhidos."""
        dados = AplicarFuncoesSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        dados = dados.validated_data
        eventos = list(self.eventos_editaveis().filter(pk__in=set(dados['evento_ids'])))
        funcoes = list(Funcao.objects.filter(equipe__in=self.equipes(), pk__in=set(dados['funcao_ids'])))
        if len(eventos) != len(set(dados['evento_ids'])) or len(funcoes) != len(set(dados['funcao_ids'])):
            raise ValidationError('Algum evento ou função não está disponível para você.')
        criadas, existentes = evento_services.aplicar_funcoes(eventos, funcoes)
        return Response({'criadas': criadas, 'existentes': existentes})


class PdfDaEscalaView(FerramentasView):
    def post(self, request):
        """Link temporário (1 hora) do PDF do mês, o mesmo do site, para abrir no navegador do celular."""
        dados = PdfDaEscalaSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        dados = dados.validated_data
        equipe = self.equipe_escolhida(dados['equipe_id'])
        return Response({'url': link_do_pdf(request.user, equipe, dados['ano'], dados['mes'], dados['estilo'])})
