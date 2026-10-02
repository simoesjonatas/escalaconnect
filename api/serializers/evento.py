from rest_framework import serializers

from evento.models import Evento


class EventoSerializer(serializers.ModelSerializer):
    equipe = serializers.CharField(source='equipe.nome', read_only=True, default=None)

    class Meta:
        model = Evento
        fields = ['id', 'nome', 'data_inicio', 'data_fim', 'observacao', 'equipe_id', 'equipe']


class JanelaCalendarioSerializer(serializers.Serializer):
    """Parâmetros de GET /eventos/. Sem datas, devolve de 30 dias atrás a 120 dias à frente."""
    inicio = serializers.DateField(required=False)
    fim = serializers.DateField(required=False)
    filtro = serializers.ChoiceField(choices=['escalado'], required=False, allow_blank=True)
    equipe = serializers.RegexField(r'^(\d+|publicos)$', required=False, allow_blank=True)

    def validate(self, dados):
        if dados.get('inicio') and dados.get('fim') and dados['fim'] < dados['inicio']:
            raise serializers.ValidationError({'fim': 'O fim precisa ser depois do início.'})
        return dados
