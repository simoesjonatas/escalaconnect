from django.shortcuts import render
from django.conf import settings
import re

class AdminRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # Lê as URLs protegidas e liberadas diretamente do settings
        self.protected_paths = getattr(settings, 'ADMIN_PROTECTED_PATHS', [])
        self.allowed_paths = getattr(settings, 'ADMIN_ALLOWED_PATHS', [])

    def __call__(self, request):
        request_path = request.path

        # Verifica se a URL atual está nas URLs liberadas
        for allowed_path in self.allowed_paths:
            if re.fullmatch(allowed_path.replace('*', '.*'), request_path):
                return self.get_response(request)

        # Verifica se a URL atual está nas URLs protegidas
        for protected_path in self.protected_paths:
            if re.fullmatch(protected_path.replace('*', '.*'), request_path):
                # Verifica se o usuário está autenticado e é administrador
                if not request.user.is_authenticated or not request.user.is_staff:
                    return render(request, '403_forbidden.html', status=403)
        
        # Processa a requisição normalmente se passar nas verificações
        response = self.get_response(request)
        return response
