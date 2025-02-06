# utils.py ou decorators.py
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from functools import wraps

def is_admin(user):
    return user.is_staff  # ou `user.is_superuser`, conforme a permissão desejada

def admin_required(view_func):
    @wraps(view_func)
    @login_required
    # @user_passes_test(is_admin, login_url=None)  # Evita redirecionamento automático
    def wrapper(request, *args, **kwargs):
        if not is_admin(request.user):
            return render(request, '403_forbidden.html', status=403)
        return view_func(request, *args, **kwargs)
    return wrapper
