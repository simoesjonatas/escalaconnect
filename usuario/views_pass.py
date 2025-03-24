from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from .models import Usuario, PasswordResetRequest
from .forms import RecuperarSenhaForm
from .mail import enviar_email_redefinicao_senha
from django.urls import reverse
from django.db.models.functions import TruncDate
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
                # Remover caracteres não numéricos do CPF
                cpf_numerico = re.sub(r'[^0-9]', '', cpf)   
                usuario = Usuario.objects.annotate(
                    aniversario_data=TruncDate('aniversario')
                ).get(
                    cpf=cpf_numerico, 
                    aniversario_data=aniversario
                )
                
                 # Desativa hashes anteriores
                PasswordResetRequest.objects.filter(usuario=usuario, is_used=False).update(is_used=True)

                # Cria nova tentativa
                reset_request = PasswordResetRequest.objects.create(usuario=usuario)

                # reset_url = request.build_absolute_uri(
                #     reverse('password_reset_confirm', args=[reset_request.hash])
                # )
                # reset_url_teste = settings.DEFAULT_DOMAIN + reverse('password_reset_confirm', args=[reset_request.hash])

                # print(reset_url)
                # print(reset_url_teste)
                # # Enviar e-mail
                enviar_email_redefinicao_senha(usuario.email,reset_request)

                return redirect('recuperar_senha_sucesso')

            except Usuario.DoesNotExist:
                form.add_error(None, 'Dados não encontrados. Verifique seu CPF e data de nascimento.')

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
                form.save()

                reset_request.is_used = True
                reset_request.reset_at = timezone.now()
                reset_request.save()

                return redirect('login')
        else:
            form = SetPasswordForm(reset_request.usuario)

        return render(request, 'usuario/password_reset_confirm.html', {'form': form})

    except PasswordResetRequest.DoesNotExist:
        return render(request, 'usuario/hash_invalido.html')
