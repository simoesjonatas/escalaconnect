from rest_framework import serializers

from escala.models import Desistencia, Escala, Rendimento, SolicitacaoTroca
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


class OfertaSerializer(serializers.ModelSerializer):
    """Voluntário que se ofereceu para uma vaga em aberto."""
    pessoa = PessoaSerializer(source='candidato')
    escala = EscalaDaEquipeSerializer()

    class Meta:
        model = Rendimento
        fields = ['id', 'data_candidatura', 'pessoa', 'escala']


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


class VagaAbertaSerializer(EscalaDaEquipeSerializer):
    """Vaga da equipe do voluntário; `me_ofereci` diz se ele já se ofereceu."""
    me_ofereci = serializers.BooleanField(read_only=True)

    class Meta(EscalaDaEquipeSerializer.Meta):
        fields = EscalaDaEquipeSerializer.Meta.fields + ['me_ofereci']


class CandidatoSerializer(PessoaSerializer):
    disponivel = serializers.BooleanField()
    se_ofereceu = serializers.BooleanField()
    servicos_no_mes = serializers.IntegerField()


class EscalarSerializer(serializers.Serializer):
    usuario_id = serializers.IntegerField()


class EscalaDoCultoSerializer(serializers.ModelSerializer):
    """Uma função no culto, vista pelo líder: quem está (ou vaga) e a situação."""
    funcao = serializers.CharField(source='funcao.nome', read_only=True)
    equipe = serializers.CharField(source='funcao.equipe.nome', read_only=True)
    pessoa = PessoaSerializer(source='usuario', allow_null=True)
    tem_impedimento = serializers.BooleanField(read_only=True)
    troca_pendente = serializers.BooleanField(read_only=True)
    # Só nas vagas (sem pessoa): quem se ofereceu e quantos membros marcaram disponibilidade.
    ofertas = serializers.SerializerMethodField()
    disponiveis = serializers.SerializerMethodField()

    class Meta:
        model = Escala
        fields = ['id', 'funcao', 'equipe', 'pessoa', 'confirmada', 'tem_impedimento', 'troca_pendente',
                  'ofertas', 'disponiveis']

    def get_ofertas(self, escala):
        return PessoaSerializer(getattr(escala, 'ofertas', []), many=True).data

    def get_disponiveis(self, escala):
        return getattr(escala, 'disponiveis', None)


class PedirDisponibilidadeSerializer(serializers.Serializer):
    equipe_id = serializers.IntegerField()
    ano = serializers.IntegerField(min_value=2000, max_value=2100)
    mes = serializers.IntegerField(min_value=1, max_value=12)
    canal = serializers.ChoiceField(choices=['app', 'todos'])
