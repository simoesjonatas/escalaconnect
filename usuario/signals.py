from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .models import RegistroLogin


@receiver(user_logged_in)
def registrar_login(sender, request, user, **kwargs):
    RegistroLogin.objects.create(usuario=user)
