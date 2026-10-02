from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

from usuario.services import termo_pendente


class ContaLiberada(BasePermission):
    """Equivalente, na API, ao FirstLoginMiddleware e ao TermoVoluntarioMiddleware.

    Em vez de redirecionar, responde 403 com um código para o app abrir a tela
    de definir senha ou de aceite do termo.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return True  # quem barra anônimo é o IsAuthenticated
        if user.is_first_login:
            raise PermissionDenied('Defina uma nova senha para continuar.', code='senha_pendente')
        if termo_pendente(user):
            raise PermissionDenied('Aceite o termo do voluntário para continuar.', code='termo_pendente')
        return True
