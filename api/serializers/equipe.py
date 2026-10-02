from rest_framework import serializers

from equipe.models import Equipe


class EquipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipe
        fields = ['id', 'nome']
