from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings

from .services import registrar_atividade, termo_pendente

class FirstLoginMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # A API do app trata o primeiro login por conta própria (403 senha_pendente).
        # Sem esta isenção ela seria redirecionada: o DRF propaga o usuário do token
        # para o request, e este middleware age depois da view.
        if request.path.startswith('/api/v1/'):
            return response
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
        if user.is_authenticated and termo_pendente(user):
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


class AtividadeMiddleware:
    """Registra a última atividade e a atividade diária de usuários autenticados.

    Grava no banco no máximo uma vez por minuto por usuário (throttle via cache)
    para não adicionar escrita a cada request.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated:
            registrar_atividade(user)
        return response
