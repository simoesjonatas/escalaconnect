from django.contrib.auth import authenticate
from django.contrib.auth.signals import user_logged_in
from knox.models import AuthToken
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..exceptions import ErroDeNegocio
from ..serializers.usuario import LoginSerializer, UsuarioSerializer
from ..throttles import LoginIPThrottle, LoginUsuarioThrottle


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

        instancia, token = AuthToken.objects.create(user=user)
        # Mesmo signal do login por sessão: grava RegistroLogin e last_login.
        user_logged_in.send(sender=user.__class__, request=request, user=user)
        return Response({
            'token': token,
            'expiry': instancia.expiry,
            'usuario': UsuarioSerializer(user).data,
        })


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
