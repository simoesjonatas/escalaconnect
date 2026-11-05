from django.contrib.auth import authenticate
from django.contrib.auth.signals import user_logged_in
from knox.models import AuthToken
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..exceptions import ErroDeNegocio, erros_do_form
from usuario.forms_signup import SignupForm
from usuario.services import mascarar_email, pedir_redefinicao_senha

from ..serializers.usuario import LoginSerializer, RecuperarSenhaSerializer, UsuarioSerializer
from ..throttles import CadastroThrottle, LoginIPThrottle, LoginUsuarioThrottle, RecuperarSenhaThrottle


def _sessao(request, user):
    """Token novo para o aparelho, no mesmo formato do login."""
    instancia, token = AuthToken.objects.create(user=user)
    # Mesmo signal do login por sessão: grava RegistroLogin e last_login.
    user_logged_in.send(sender=user.__class__, request=request, user=user)
    return Response({
        'token': token,
        'expiry': instancia.expiry,
        'usuario': UsuarioSerializer(user).data,
    })


class LoginView(APIView):
    """POST {username, password} -> {token, expiry, usuario}. Aceita usuário ou e-mail."""
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [LoginIPThrottle, LoginUsuarioThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(request, **serializer.validated_data)
        if user is None:
            # 400 e não 401: no app, 401 significa "token inválido, volte ao login".
            raise ErroDeNegocio('Usuário ou senha inválidos.', code='credenciais_invalidas')

        return _sessao(request, user)


CAMPOS_DO_CADASTRO = ['first_name', 'last_name', 'email', 'cpf', 'telefone', 'aniversario', 'password1', 'password2']


class CadastroView(APIView):
    """POST: cria a conta (mesmas regras do cadastro do site) e já entra, como no login.

    A data de nascimento é obrigatória no app: é com ela e o CPF que se recupera a senha.
    O termo do voluntário fica pendente, e o app abre a tela de aceite logo em seguida.
    """
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [CadastroThrottle]

    def post(self, request):
        dados = {campo: request.data.get(campo) or '' for campo in CAMPOS_DO_CADASTRO}
        form = SignupForm({**dados, 'aceitar_termos': 'on'})
        valido = form.is_valid()
        if not dados['aniversario']:
            form.add_error('aniversario', 'Informe sua data de nascimento: ela é usada para recuperar a senha.')
            valido = False
        if not valido:
            raise erros_do_form(form)
        user = form.save(commit=False)
        user.is_first_login = False  # a senha já foi escolhida agora
        user.save()
        return _sessao(request, user)


class RecuperarSenhaView(APIView):
    """POST {cpf, data_nascimento} -> {email}: manda o link para criar senha nova (mesmo fluxo do site)."""
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [RecuperarSenhaThrottle]

    def post(self, request):
        serializer = RecuperarSenhaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = pedir_redefinicao_senha(serializer.validated_data['cpf'], serializer.validated_data['data_nascimento'])
        return Response({'email': mascarar_email(usuario.email)})


class LogoutView(APIView):
    """Revoga o token deste aparelho."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.auth.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LogoutAllView(APIView):
    """Revoga todos os tokens do usuário (sair de todos os aparelhos)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.user.auth_token_set.all().delete()
        request.user.devices.update(ativo=False)
        return Response(status=status.HTTP_204_NO_CONTENT)
