"""Escala fixa da equipe no app do líder: mesmas regras do site (escala/fixa.py)."""
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.response import Response

from escala import fixa
from escala.models import EscalaFixaItem, Funcao

from ..serializers.lideranca import PessoaSerializer
from .lideranca import LiderView

User = get_user_model()


class LinhaSerializer(serializers.Serializer):
    dia_semana = serializers.IntegerField()
    turno = serializers.CharField()
    semana = serializers.IntegerField()
    funcao_id = serializers.IntegerField()
    usuario_id = serializers.IntegerField()


class AtivaSerializer(serializers.Serializer):
    ativa = serializers.BooleanField()


def _item(item):
    return {
        'id': item.pk,
        'dia_semana': item.dia_semana,
        'turno': item.turno,
        'semana': item.semana,
        'culto': fixa.rotulo_do_culto(item.dia_semana, item.turno),
        'quando': fixa.rotulo_da_semana(item.dia_semana, item.semana),
        'funcao': {'id': item.funcao_id, 'nome': item.funcao.nome},
        'usuario': PessoaSerializer(item.usuario).data,
    }


def _resultado(resultado):
    return {
        'resumo': fixa.descrever_resultado(resultado),
        'preenchidas': resultado['preenchidas'],
        'liberadas': resultado['liberadas'],
        'puladas': resultado['puladas'],
        'nao_alteradas': resultado['nao_alteradas'],
    }


class EscalaFixaView(LiderView):
    def get_equipe(self, pk):
        return get_object_or_404(self.equipes(), pk=pk)

    def get(self, request, pk):
        """Configuração da escala fixa, com as funções e os integrantes para montar as linhas."""
        equipe = self.get_equipe(pk)
        config = fixa.escala_fixa_da_equipe(equipe)
        itens = config.itens.select_related('funcao', 'usuario').order_by('dia_semana', 'turno', 'semana',
                                                                          'funcao__nome', 'pk')
        membros = (User.objects.filter(membrosequipe__equipe=equipe, membrosequipe__aprovado=True)
                   .order_by('first_name', 'last_name', 'username'))
        return Response({
            'equipe': {'id': equipe.pk, 'nome': equipe.nome},
            'ativa': config.ativa,
            'itens': [_item(i) for i in itens],
            'funcoes': [{'id': f.pk, 'nome': f.nome} for f in Funcao.objects.filter(equipe=equipe).order_by('nome')],
            'membros': PessoaSerializer(membros, many=True).data,
        })

    def patch(self, request, pk):
        """Liga ou desliga. Ao ligar, preenche os cultos já cadastrados."""
        equipe = self.get_equipe(pk)
        dados = AtivaSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        return Response(_resultado(fixa.definir_ativa(equipe, dados.validated_data['ativa'])))


def _linha(request, equipe):
    dados = LinhaSerializer(data=request.data)
    dados.is_valid(raise_exception=True)
    d = dados.validated_data
    return {
        'dia_semana': d['dia_semana'],
        'turno': d['turno'],
        'semana': d['semana'],
        'funcao': get_object_or_404(Funcao, pk=d['funcao_id'], equipe=equipe),
        'usuario': get_object_or_404(User, pk=d['usuario_id']),
    }


class ItensDaEscalaFixaView(EscalaFixaView):
    def post(self, request, pk):
        equipe = self.get_equipe(pk)
        item, resultado = fixa.adicionar_item(equipe, **_linha(request, equipe))
        return Response({'item': _item(item), **_resultado(resultado)}, status=201)


class ItemDaEscalaFixaView(LiderView):
    def get_item(self, pk):
        return get_object_or_404(
            EscalaFixaItem.objects.select_related('escala_fixa__equipe', 'funcao', 'usuario'),
            pk=pk, escala_fixa__equipe__in=self.equipes(),
        )

    def patch(self, request, pk):
        item = self.get_item(pk)
        resultado = fixa.atualizar_item(item, **_linha(request, item.escala_fixa.equipe))
        item.refresh_from_db()
        return Response({'item': _item(item), **_resultado(resultado)})

    def delete(self, request, pk):
        return Response(_resultado(fixa.excluir_item(self.get_item(pk))))
