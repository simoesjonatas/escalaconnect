from rest_framework import serializers

from escala.models import Desistencia, Escala, SolicitacaoTroca
from equipe.models import MembrosEquipe

from .escala import EventoResumoSerializer


class PessoaSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nome = serializers.SerializerMethodField()

    def get_nome(self, usuario):
        return usuario.get_full_name() or usuario.username


class EscalaDaEquipeSerializer(serializers.ModelSerializer):
    """Escala vista pelo líder (de qualquer voluntário da equipe)."""
    evento = EventoResumoSerializer(read_only=True)
    funcao = serializers.CharField(source='funcao.nome', read_only=True)
    equipe = serializers.CharField(source='funcao.equipe.nome', read_only=True)
    equipe_id = serializers.IntegerField(source='funcao.equipe_id', read_only=True)

    class Meta:
        model = Escala
        fields = ['id', 'evento', 'funcao', 'equipe', 'equipe_id', 'confirmada']


class ImpedimentoSerializer(serializers.ModelSerializer):
    pessoa = PessoaSerializer(source='usuario')
    escala = EscalaDaEquipeSerializer()

    class Meta:
        model = Desistencia
        fields = ['id', 'motivo', 'data_solicitacao', 'pessoa', 'escala']


class TrocaSerializer(serializers.ModelSerializer):
    pessoa = PessoaSerializer(source='solicitante')
    escala = EscalaDaEquipeSerializer(source='escala_origem')

    class Meta:
        model = SolicitacaoTroca
        fields = ['id', 'data_solicitacao', 'pessoa', 'escala']


class CandidaturaSerializer(serializers.ModelSerializer):
    pessoa = PessoaSerializer(source='usuario')
    equipe = serializers.CharField(source='equipe.nome')
    equipe_id = serializers.IntegerField()

    class Meta:
        model = MembrosEquipe
        fields = ['id', 'pessoa', 'equipe', 'equipe_id']


class VagaSerializer(EscalaDaEquipeSerializer):
    disponiveis = serializers.IntegerField(read_only=True)

    class Meta(EscalaDaEquipeSerializer.Meta):
        fields = EscalaDaEquipeSerializer.Meta.fields + ['disponiveis']


class CandidatoSerializer(PessoaSerializer):
    disponivel = serializers.BooleanField()
    servicos_no_mes = serializers.IntegerField()


class EscalarSerializer(serializers.Serializer):
    usuario_id = serializers.IntegerField()
