from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from .models import Usuario, PasswordResetRequest
from .forms import RecuperarSenhaForm
from .services import pedir_redefinicao_senha
from escalaconnect.regras import RegraDeNegocio
from django.urls import reverse
from django.utils import timezone
from django.conf import settings
import re

@login_required
def set_password(request):
    if request.method == 'POST':
        form = SetPasswordForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            user.is_first_login = False
            user.save()
            # Trocar a senha do próprio usuário logado invalida o hash da sessão;
            # sem isto o usuário é deslogado na requisição seguinte (caía no /login/
            # logo após definir a senha).
            update_session_auth_hash(request, user)
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


def recuperar_senha(request):
    if request.method == 'POST':
        form = RecuperarSenhaForm(request.POST)
        if form.is_valid():
            cpf = form.cleaned_data['cpf']
            aniversario = form.cleaned_data['data_nascimento']
            
            try:
                pedir_redefinicao_senha(cpf, aniversario)
                return redirect('recuperar_senha_sucesso')
            except RegraDeNegocio as erro:
                form.add_error(None, str(erro))

    else:
        form = RecuperarSenhaForm()

    return render(request, 'usuario/recuperar_senha.html', {'form': form})

def recuperar_senha_sucesso(request):
    return render(request, 'usuario/recuperar_senha_sucesso.html')

def password_reset_confirm(request, hash):
    try:
        reset_request = PasswordResetRequest.objects.get(hash=hash)

        if not reset_request.hash_valido():
            return render(request, 'usuario/hash_invalido.html')

        if request.method == 'POST':
            form = SetPasswordForm(reset_request.usuario, request.POST)
            if form.is_valid():
                user = form.save()

                # O usuário acabou de definir a própria senha pelo link do e-mail:
                # não faz sentido forçá-lo a trocar de novo no primeiro login
                # (evita o passo redundante de set_password ao entrar).
                if user.is_first_login:
                    user.is_first_login = False
                    user.save(update_fields=['is_first_login'])

                reset_request.is_used = True
                reset_request.reset_at = timezone.now()
                reset_request.save()

                return redirect('login')
        else:
            form = SetPasswordForm(reset_request.usuario)

        return render(request, 'usuario/password_reset_confirm.html', {'form': form})

    except PasswordResetRequest.DoesNotExist:
        return render(request, 'usuario/hash_invalido.html')
