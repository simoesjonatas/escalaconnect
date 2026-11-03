from django.utils import timezone
from rest_framework import serializers


def _ids_unicos(valores):
    return list(dict.fromkeys(valores))


class NovoEventoSerializer(serializers.Serializer):
    """Mesmos campos do formulário "Criar Evento" do site, mais as funções (vagas) do evento."""
    nome = serializers.CharField(max_length=255)
    # Nulo = evento público, só para admin (o líder cria eventos da equipe dele).
    equipe_id = serializers.IntegerField(allow_null=True)
    data_inicio = serializers.DateTimeField()
    data_fim = serializers.DateTimeField()
    observacao = serializers.CharField(required=False, allow_blank=True, default='')
    funcao_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)

    def validate(self, dados):
        if dados['data_fim'] <= dados['data_inicio']:
            raise serializers.ValidationError({'data_fim': 'O fim precisa ser depois do início.'})
        if dados['data_inicio'] <= timezone.now():
            raise serializers.ValidationError({'data_inicio': 'Escolha uma data futura.'})
        dados['funcao_ids'] = _ids_unicos(dados['funcao_ids'])
        return dados


class EventosEmMassaSerializer(serializers.Serializer):
    """Mesmos campos do "Gerar em Massa" do site: nome, equipe, meses, dias da semana e horário."""
    nome = serializers.CharField(max_length=255)
    equipe_id = serializers.IntegerField()
    meses = serializers.ListField(child=serializers.RegexField(r'^\d{4}-\d{2}$'), min_length=1)
    # 0 = segunda ... 6 = domingo (date.weekday), como no site.
    dias_da_semana = serializers.ListField(child=serializers.IntegerField(min_value=0, max_value=6), min_length=1)
    horario_inicio = serializers.TimeField()
    horario_fim = serializers.TimeField()
    observacao = serializers.CharField(required=False, allow_blank=True, default='')
    funcao_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)

    def validate(self, dados):
        if dados['horario_fim'] <= dados['horario_inicio']:
            raise serializers.ValidationError({'horario_fim': 'O término precisa ser depois do início.'})
        dados['funcao_ids'] = _ids_unicos(dados['funcao_ids'])
        return dados


class AplicarFuncoesSerializer(serializers.Serializer):
    evento_ids = serializers.ListField(child=serializers.IntegerField(), min_length=1)
    funcao_ids = serializers.ListField(child=serializers.IntegerField(), min_length=1)


class PdfDaEscalaSerializer(serializers.Serializer):
    equipe_id = serializers.IntegerField()
    ano = serializers.IntegerField(min_value=2000, max_value=2100)
    mes = serializers.IntegerField(min_value=1, max_value=12)
    estilo = serializers.ChoiceField(choices=['connect', 'escuro', 'mural'], default='connect')
