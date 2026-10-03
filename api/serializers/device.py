from rest_framework import serializers

from ..models import Device


class DeviceSerializer(serializers.Serializer):
    # Sem validador de unicidade: registrar um token já conhecido atualiza o aparelho.
    expo_token = serializers.RegexField(r'^Expo(nent)?PushToken\[[^\]]+\]$', max_length=255)
    plataforma = serializers.ChoiceField(choices=[p for p, _ in Device.PLATAFORMAS])
    nome_aparelho = serializers.CharField(max_length=100, required=False, allow_blank=True)
    app_versao = serializers.CharField(max_length=30, required=False, allow_blank=True)
