from rest_framework import serializers

from escala.models import Escala
from evento.models import Evento


class EventoResumoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evento
        fields = ['id', 'nome', 'data_inicio', 'data_fim', 'observacao']


class EscalaSerializer(serializers.ModelSerializer):
    """Escala do próprio voluntário. Espera o queryset de api.views.escalas.escalas_do_usuario."""
    evento = EventoResumoSerializer(read_only=True)
    funcao = serializers.CharField(source='funcao.nome', read_only=True)
    equipe = serializers.CharField(source='funcao.equipe.nome', read_only=True)
    equipe_id = serializers.IntegerField(source='funcao.equipe_id', read_only=True)
    tem_impedimento = serializers.BooleanField(read_only=True)
    troca_pendente = serializers.BooleanField(read_only=True)

    class Meta:
        model = Escala
        fields = [
            'id', 'evento', 'funcao', 'equipe', 'equipe_id',
            'confirmada', 'data_confirmacao', 'tem_impedimento', 'troca_pendente',
        ]


class ImpedimentoSerializer(serializers.Serializer):
    motivo = serializers.CharField()
