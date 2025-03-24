from celery import shared_task
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from evento.models import Evento

@shared_task
def enviar_email_confirmacao_task(nome, email):
    contexto = {'evento': nome}
    assunto = f'Confirmação de Escala: {nome} - ESCALA CONNECT - PIBVP'
    corpo_email = render_to_string('email/confirmacao_email.html', contexto)
    email = EmailMessage(
        subject=assunto,
        body=corpo_email,
        to=[email]
    )
    email.content_subtype = 'html'
    email.send()
