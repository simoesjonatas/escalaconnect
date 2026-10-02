from django.conf import settings
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from django.template.loader import render_to_string
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from usuario.forms import PerfilContatoForm
from usuario.services import aceitar_termo

from ..exceptions import ErroDeNegocio, erros_do_form
from ..permissions import ContaLiberada
from ..serializers.usuario import DefinirSenhaSerializer, TrocarSenhaSerializer, UsuarioSerializer


class MeView(APIView):
    """GET: dados e pendências do usuário. PATCH: atualiza e-mail e telefone."""

    def get_permissions(self):
        # O GET fica liberado com senha/termo pendentes: é por ele que o app
        # descobre qual tela abrir.
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return [IsAuthenticated(), ContaLiberada()]

    def get(self, request):
        return Response(UsuarioSerializer(request.user).data)

    def patch(self, request):
        user = request.user
        form = PerfilContatoForm(
            {
                'email': request.data.get('email', user.email),
                'telefone': request.data.get('telefone', user.telefone),
            },
            instance=user,
        )
        if not form.is_valid():
            raise erros_do_form(form)
        form.save()
        return Response(UsuarioSerializer(user).data)


class MetaView(APIView):
    """Versão mínima do app aceita e link do APK atual (consultado antes do login)."""
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            'min_build': settings.APP_MIN_BUILD,
            'apk_url': settings.APP_APK_URL,
        })


class TermoView(APIView):
    """Texto do termo do voluntário (o mesmo trecho HTML exibido no site)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({'html': render_to_string('usuario/_termo_texto.html')})


class AceitarTermoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.termo_aceito_em is None:
            aceitar_termo(request.user)
        return Response(UsuarioSerializer(request.user).data)


def _erros_de_senha(form, campos):
    """Erros de um form de senha do Django, com os nomes de campo da API."""
    return ValidationError({
        campos.get(campo, campo): [str(erro) for erro in erros]
        for campo, erros in form.errors.items()
    })


class DefinirSenhaView(APIView):
    """Define a senha no primeiro login (conta criada pelo líder com senha provisória)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.is_first_login:
            raise ErroDeNegocio('A senha inicial já foi definida. Use a troca de senha.', code='senha_ja_definida')
        serializer = DefinirSenhaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        senha = serializer.validated_data['nova_senha']
        form = SetPasswordForm(request.user, {'new_password1': senha, 'new_password2': senha})
        if not form.is_valid():
            raise _erros_de_senha(form, {'new_password1': 'nova_senha', 'new_password2': 'nova_senha'})
        user = form.save()
        user.is_first_login = False
        user.save()
        return Response(UsuarioSerializer(user).data)


class TrocarSenhaView(APIView):
    """Troca a senha e desconecta os outros aparelhos (o token atual continua válido)."""

    def post(self, request):
        serializer = TrocarSenhaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dados = serializer.validated_data
        form = PasswordChangeForm(request.user, {
            'old_password': dados['senha_atual'],
            'new_password1': dados['nova_senha'],
            'new_password2': dados['nova_senha'],
        })
        if not form.is_valid():
            raise _erros_de_senha(form, {
                'old_password': 'senha_atual', 'new_password1': 'nova_senha', 'new_password2': 'nova_senha'})
        form.save()
        request.user.auth_token_set.exclude(pk=request.auth.pk).delete()
        return Response(status=204)
