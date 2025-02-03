from django.shortcuts import redirect
from django.urls import reverse

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
