from django.contrib.auth import get_user_model
from rest_framework import serializers

from usuario.services import termo_pendente


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()  # nome de usuário ou e-mail
    password = serializers.CharField(trim_whitespace=False)


class UsuarioSerializer(serializers.ModelSerializer):
    """Dados do próprio usuário. Campos explícitos: o CPF nunca sai pela API."""
    nome_completo = serializers.CharField(source='get_full_name', read_only=True)
    precisa_definir_senha = serializers.BooleanField(source='is_first_login', read_only=True)
    precisa_aceitar_termo = serializers.SerializerMethodField()
    em_equipe = serializers.SerializerMethodField()
    lider = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = [
            'id', 'username', 'first_name', 'last_name', 'nome_completo',
            'email', 'telefone', 'aniversario',
            'precisa_definir_senha', 'precisa_aceitar_termo', 'em_equipe', 'lider',
        ]
        read_only_fields = fields

    def get_precisa_aceitar_termo(self, user):
        return termo_pendente(user)

    def get_em_equipe(self, user):
        return user.is_in_team()

    def get_lider(self, user):
        return user.is_leader()


class DefinirSenhaSerializer(serializers.Serializer):
    nova_senha = serializers.CharField(trim_whitespace=False)


class TrocarSenhaSerializer(serializers.Serializer):
    senha_atual = serializers.CharField(trim_whitespace=False)
    nova_senha = serializers.CharField(trim_whitespace=False)
