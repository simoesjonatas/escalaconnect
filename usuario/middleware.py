from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings

class FirstLoginMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # Verifique se o usuário está autenticado e se é seu primeiro login
        if request.user.is_authenticated and request.user.is_first_login:
            # Verifique se o caminho atual não é o de definir senha ou logout
            if not (request.path.startswith(reverse('set_password')) or request.path.startswith(reverse('logout'))):
                return redirect('set_password')  # Redirecionar para a página de definir senha
        return response


class TermoVoluntarioMiddleware:
    """Exige o aceite do termo de compromisso do voluntário antes de usar o sistema.

    Usuários autenticados que ainda não aceitaram (termo_aceito_em is None) são
    redirecionados para a página de aceite. Superusuários e staff ficam isentos, e
    algumas rotas seguem liberadas (o próprio termo, set_password, logout, admin e
    estáticos) para não criar loop de redirecionamento.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if (user.is_authenticated and not (user.is_staff or user.is_superuser)
                and user.termo_aceito_em is None):
            liberados = (
                reverse('aceitar_termo'),
                reverse('set_password'),
                reverse('logout'),
            )
            path = request.path
            isento = (
                path.startswith('/admin/')
                or path.startswith(settings.STATIC_URL)
                or any(path.startswith(p) for p in liberados)
            )
            if not isento:
                return redirect('aceitar_termo')
        return self.get_response(request)
