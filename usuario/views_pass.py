from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from .models import Usuario
@login_required
def set_password(request):
    if request.method == 'POST':
        form = SetPasswordForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            user.is_first_login = False
            user.save()
            return redirect('base_page')
    else:
        form = SetPasswordForm(request.user)
    return render(request, 'set_password.html', {'form': form})


@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Sua senha foi atualizada com sucesso!')
            return redirect('base_page')
        else:
            messages.error(request, 'Por favor, corrija o erro abaixo.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'change_password.html', {
        'form': form
    })


def can_reset_password(user):
    # Verificar se o usuário é líder de equipe, staff ou superuser
    return user.groups.filter(name='Lideres').exists() or user.is_staff or user.is_superuser

def is_leader(user):
    return user.groups.filter(name='Lideres').exists()  # Substitua pela sua lógica de líder

@login_required
@user_passes_test(can_reset_password)
def reset_user_password(request, user_id):
    user = get_object_or_404(Usuario, pk=user_id)
    if request.method == 'POST':
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            user.is_first_login = True  # forca o usuario a mudar a senha no proximo login
            user.save()
            messages.success(request, "Senha resetada com sucesso. O usuário deve mudar a senha no próximo login.")
            return redirect('base_page') 
    else:
        form = SetPasswordForm(user)
    
    return render(request, 'reset_password.html', {'form': form, 'usuario': user})
