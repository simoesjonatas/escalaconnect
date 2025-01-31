from django.core.exceptions import PermissionDenied
from functools import wraps
from equipe.models import Lideranca

def require_lideranca(view_func):
    """
    Decorador que verifica se o usuário faz parte da liderança da equipe.
    Se for superusuário ou staff, tem acesso automaticamente.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        equipe_id = kwargs.get('equipe_pk') or kwargs.get('pk')  # Obtém o ID da equipe

        if not equipe_id:
            raise PermissionDenied("Equipe não especificada.")

        # Verifica se o usuário tem permissão
        if not (request.user.is_superuser or request.user.is_staff or 
                Lideranca.objects.filter(usuario=request.user, equipe_id=equipe_id).exists()):
            raise PermissionDenied("Você não tem permissão para acessar esta página.")

        return view_func(request, *args, **kwargs)

    return _wrapped_view
