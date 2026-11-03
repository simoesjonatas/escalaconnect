"""Gestão da equipe pelo líder no app: funções, lideranças e integrantes.

Mesmos papéis do site (equipe.services): o líder cria, renomeia e exclui funções sem
escalas, adiciona e remove integrantes e remove lideranças. Renomear a equipe é só do admin;
adicionar líderes continua pelo site, também só admin.
"""
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from equipe import services as equipe_services
from equipe.models import Lideranca, MembrosEquipe
from escala.models import Escala, Funcao

from ..serializers.lideranca import PessoaSerializer
from .lideranca import LiderView


class NomeSerializer(serializers.Serializer):
    nome = serializers.CharField(max_length=255)


class IntegranteSerializer(serializers.Serializer):
    usuario_id = serializers.IntegerField()


def _admin(usuario):
    return usuario.is_staff or usuario.is_superuser


def _pessoa(usuario):
    return PessoaSerializer(usuario).data


class EquipeDoLiderView(LiderView):
    def get_equipe(self, pk):
        return get_object_or_404(self.equipes(), pk=pk)

    def get(self, request, pk):
        """Funções (com quantas escalas cada uma tem), líderes, integrantes e candidaturas da equipe."""
        equipe = self.get_equipe(pk)
        funcoes = (Funcao.objects.filter(equipe=equipe).annotate(escalas=Count('escala')).order_by('nome'))
        liderancas = list(Lideranca.objects.filter(equipe=equipe).select_related('usuario'))
        lideres = {l.usuario_id for l in liderancas}
        membros = list(MembrosEquipe.objects.filter(equipe=equipe).select_related('usuario'))
        futuras = dict(
            Escala.objects
            .filter(funcao__equipe=equipe, usuario__in=[m.usuario_id for m in membros if m.aprovado],
                    evento__data_inicio__gte=timezone.now())
            .values('usuario_id').annotate(n=Count('id')).values_list('usuario_id', 'n')
        )
        nome = lambda u: (u.get_full_name() or u.username).lower()  # noqa: E731
        return Response({
            'id': equipe.pk,
            'nome': equipe.nome,
            'pode_renomear': _admin(request.user),
            'funcoes': [{'id': f.pk, 'nome': f.nome, 'escalas': f.escalas} for f in funcoes],
            'lideres': [
                {'id': l.pk, 'pessoa': _pessoa(l.usuario), 'sou_eu': l.usuario_id == request.user.pk}
                for l in sorted(liderancas, key=lambda l: nome(l.usuario))
            ],
            'integrantes': [
                {'id': m.pk, 'pessoa': _pessoa(m.usuario), 'lider': m.usuario_id in lideres,
                 'escalas_futuras': futuras.get(m.usuario_id, 0)}
                for m in sorted((m for m in membros if m.aprovado), key=lambda m: nome(m.usuario))
            ],
            'pendentes': [
                {'id': m.pk, 'pessoa': _pessoa(m.usuario)}
                for m in sorted((m for m in membros if not m.aprovado), key=lambda m: nome(m.usuario))
            ],
        })

    def patch(self, request, pk):
        """Renomear a equipe: só admin, como no site."""
        if not _admin(request.user):
            raise PermissionDenied('Só o admin pode trocar o nome da equipe.')
        equipe = self.get_equipe(pk)
        dados = NomeSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        equipe.nome = dados.validated_data['nome'].strip()
        equipe.save(update_fields=['nome'])
        return Response({'id': equipe.pk, 'nome': equipe.nome})


class FuncoesDaEquipeView(EquipeDoLiderView):
    http_method_names = ['post', 'options']

    def post(self, request, pk):
        dados = NomeSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        funcao = equipe_services.criar_funcao(self.get_equipe(pk), dados.validated_data['nome'])
        return Response({'id': funcao.pk, 'nome': funcao.nome, 'escalas': 0}, status=201)


class FuncaoView(LiderView):
    def get_funcao(self, pk):
        return get_object_or_404(Funcao.objects.filter(equipe__in=self.equipes()), pk=pk)

    def patch(self, request, pk):
        dados = NomeSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        funcao = equipe_services.renomear_funcao(self.get_funcao(pk), dados.validated_data['nome'])
        return Response({'id': funcao.pk, 'nome': funcao.nome})

    def delete(self, request, pk):
        equipe_services.excluir_funcao(self.get_funcao(pk))
        return Response(status=204)


class LiderancaView(LiderView):
    def delete(self, request, pk):
        lideranca = get_object_or_404(Lideranca.objects.filter(equipe__in=self.equipes()), pk=pk)
        equipe_services.remover_lideranca(lideranca)
        return Response(status=204)


class IntegrantesView(EquipeDoLiderView):
    http_method_names = ['get', 'post', 'options']

    def get(self, request, pk):
        """Busca quem pode entrar na equipe (ativos que ainda não são integrantes), por nome ou usuário."""
        equipe = self.get_equipe(pk)
        termo = (request.query_params.get('q') or '').strip()
        if len(termo) < 2:
            return Response([])
        filtro = Q()
        for parte in termo.split():
            filtro &= Q(first_name__icontains=parte) | Q(last_name__icontains=parte) | Q(username__icontains=parte)
        aprovados = MembrosEquipe.objects.filter(equipe=equipe, aprovado=True).values('usuario_id')
        usuarios = (get_user_model().objects.filter(filtro, is_active=True).exclude(pk__in=aprovados)
                    .order_by('first_name', 'last_name', 'username')[:20])
        return Response([_pessoa(u) for u in usuarios])

    def post(self, request, pk):
        equipe = self.get_equipe(pk)
        dados = IntegranteSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        usuario = get_object_or_404(get_user_model(), pk=dados.validated_data['usuario_id'], is_active=True)
        membro = equipe_services.adicionar_integrante(equipe, usuario)
        return Response({'id': membro.pk, 'pessoa': _pessoa(usuario)}, status=201)


class IntegranteView(LiderView):
    def delete(self, request, pk):
        membro = get_object_or_404(MembrosEquipe.objects.filter(equipe__in=self.equipes(), aprovado=True), pk=pk)
        equipe_services.remover_integrante(membro)
        return Response(status=204)
