from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.shortcuts import render

def pagina_teste_emails(request):
    return render(request, 'email/testar_emails.html')


def view_enviar_confirmacao(request):
    email = request.GET.get('email', '')  # Pega o email do query string
    evento = request.GET.get('evento', '')  # Pega o nome do evento do query string
    if email and evento:
        enviar_email_confirmacao(email, evento)
        return HttpResponse("Email de confirmação enviado com sucesso!")
    else:
        return HttpResponse("Email ou evento não especificado.", status=400)

def view_enviar_lembrete(request):
    email = request.GET.get('email', '')  # Pega o email do query string
    evento = request.GET.get('evento', '')  # Pega o nome do evento do query string
    if email and evento:
        enviar_email_lembrete(email, evento)
        return HttpResponse("Email de lembrete enviado com sucesso!")
    else:
        return HttpResponse("Email ou evento não especificado.", status=400)


def enviar_email_confirmacao(email, evento):
    contexto = {'evento': evento}
    assunto = f'Confirmação de Escala: {evento} - ESCALA CONNECT - PIBVP'
    corpo_email = render_to_string('email/confirmacao_email.html', contexto)
    email = EmailMessage(
        subject=assunto,
        body=corpo_email,
        # from_email='jonatasimoes.js@gmail.com',
        to=[email]
    )
    email.content_subtype = 'html'  # Especifica que o conteúdo é HTML
    email.send()

def enviar_email_lembrete(email, evento):
    contexto = {'evento': evento}
    assunto = 'Lembrete de Escala'
    corpo_email = render_to_string('email/lembrete_email.html', contexto)
    email = EmailMessage(
        subject=assunto,
        body=corpo_email,
        from_email='jonatasimoes.js@gmail.com',
        to=[email]
    )
    email.content_subtype = 'html'  # Especifica que o conteúdo é HTML
    email.send()
    
from django.conf import settings
from django.urls import reverse


def enviar_email_redefinicao_senha(email_usuario, reset_request):
    reset_link = settings.DEFAULT_DOMAIN + reverse('password_reset_confirm', args=[reset_request.hash])
    # print("reset_link")
    # print(reset_link)
    contexto = {'reset_link': reset_link}
    assunto = 'Redefinição de Senha - ESCALACONNECT'
    corpo_email = render_to_string('email/redefinicao_senha.html', contexto)

    email = EmailMessage(
        subject=assunto,
        body=corpo_email,
        to=[email_usuario]
    )
    email.content_subtype = 'html'
    email.send()
