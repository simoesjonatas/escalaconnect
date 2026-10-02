import hashlib

from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle


class LoginIPThrottle(AnonRateThrottle):
    scope = 'login_ip'


class LoginUsuarioThrottle(SimpleRateThrottle):
    """Limita tentativas de login por usuário/e-mail informado, venha de onde vier."""
    scope = 'login_usuario'

    def get_cache_key(self, request, view):
        username = str(request.data.get('username') or '').strip().lower()
        if not username:
            return None
        ident = hashlib.sha256(username.encode()).hexdigest()
        return self.cache_format % {'scope': self.scope, 'ident': ident}
