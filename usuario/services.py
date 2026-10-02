from django.core.cache import cache
from django.db import IntegrityError
from django.utils import timezone


def termo_pendente(user):
    """True se o usuário ainda precisa aceitar o termo do voluntário (staff é isento)."""
    return not (user.is_staff or user.is_superuser) and user.termo_aceito_em is None


def registrar_atividade(user):
    """Registra a última atividade e a atividade diária do usuário.

    Grava no banco no máximo uma vez por minuto por usuário (throttle via cache)
    para não adicionar escrita a cada request. Usado pelo site (AtividadeMiddleware)
    e pela API do app (autenticação por token).
    """
    chave = f'atividade-usuario-{user.pk}'
    if cache.get(chave) is not None:
        return
    cache.set(chave, 1, 60)
    from .models import AtividadeDiaria, Usuario
    agora = timezone.now()
    Usuario.objects.filter(pk=user.pk).update(ultima_atividade=agora)
    try:
        AtividadeDiaria.objects.get_or_create(usuario_id=user.pk, data=timezone.localdate(agora))
    except IntegrityError:
        # Corrida entre workers: o registro do dia já existe.
        pass


def aceitar_termo(user):
    """Registra o aceite do termo de compromisso do voluntário."""
    user.termo_aceito_em = timezone.now()
    user.save(update_fields=['termo_aceito_em'])
