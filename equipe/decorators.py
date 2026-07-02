from functools import wraps
from django.shortcuts import render
from equipe.models import Lideranca

def require_lideranca(view_func):
    """
    Decorador que verifica se o usuário faz parte da liderança da equipe.
    Se for superusuário ou staff, tem acesso automaticamente.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # O ID da equipe pode vir como equipe_pk, equipe_id ou pk dependendo da rota.
        equipe_id = kwargs.get('equipe_pk') or kwargs.get('equipe_id') or kwargs.get('pk')

        # print("super user")
        # Permite acesso se for superusuário ou staff
        if request.user.is_superuser or request.user.is_staff:
            return view_func(request, *args, **kwargs)
        
        if not equipe_id:
            return render(request, '403_forbidden.html', status=403)


        # Verifica se o usuário é líder da equipe
        if not Lideranca.objects.filter(usuario=request.user, equipe_id=equipe_id).exists():
            return render(request, '403_forbidden.html', status=403)

        return view_func(request, *args, **kwargs)

    return _wrapped_view


def require_lider(view_func):
    """
    Decorador que verifica se o usuário faz parte da liderança da equipe.
    Se for superusuário ou staff, tem acesso automaticamente.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # print("super user")
        # print(request.user.is_leader())
        # Permite acesso se for superusuário ou staff
        if request.user.is_superuser or request.user.is_staff or request.user.is_leader():
            return view_func(request, *args, **kwargs)
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def require_lider_ou_staff(view_func):
    """
    Libera a view para admin (staff/superuser) ou para qualquer usuário que seja
    líder de pelo menos uma equipe. Caso contrário, retorna 403.

    Usado em rotas que não têm um equipe_id na URL (ex.: criar evento), onde a
    equipe é escolhida dentro do próprio formulário.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = request.user
        if user.is_authenticated and (user.is_superuser or user.is_staff or user.is_leader()):
            return view_func(request, *args, **kwargs)
        return render(request, '403_forbidden.html', status=403)

    return _wrapped_view
# {% if request.user.is_staff or request.user.is_superuser or is_leader %}