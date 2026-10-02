from rest_framework import serializers


class PeriodoSerializer(serializers.Serializer):
    """Disponibilidade ou indisponibilidade do voluntário (mesma forma nos dois models)."""
    id = serializers.IntegerField(read_only=True)
    data_inicio = serializers.DateTimeField()
    data_fim = serializers.DateTimeField()
    evento_id = serializers.IntegerField(read_only=True)
    evento = serializers.CharField(source='evento.nome', read_only=True, default=None)


class PorEventoSerializer(serializers.Serializer):
    evento_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), allow_empty=False)
