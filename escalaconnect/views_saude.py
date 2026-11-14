"""Endpoint de saúde do Celery, para monitoramento externo (docs/monitoramento-celery.md)."""
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from . import monitor_fila


@never_cache
@require_GET
def saude_celery(request):
    """200 com tudo certo; 503 quando a fila recusa tarefas ou o worker/beat não bate.

    Publica um batimento de teste (no máx. um a cada 30 s) e, com problema, avisa os admins por
    e-mail (com o mesmo limite dos outros avisos). Sem login: só diz o que está parado e há quanto
    tempo. Responde em /healthz/celery com ou sem a barra final (sem redirecionar: um monitor
    que trata 301 como sucesso veria "ok" com a fila parada).
    """
    estado = monitor_fila.estado(publicar=True)
    problemas = estado.pop('problemas')
    monitor_fila.avisar(problemas)
    return JsonResponse(
        {'ok': not problemas, 'problemas': [p.como_dict() for p in problemas], **estado},
        status=503 if problemas else 200,
        json_dumps_params={'ensure_ascii': False},
    )
