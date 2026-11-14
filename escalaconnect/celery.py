import os
import logging

from celery import Celery

logger = logging.getLogger(__name__)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "escalaconnect.settings")

app = Celery("escalaconnect")
# Puxa configurações prefixadas com CELERY_ do settings
app.config_from_object("django.conf:settings", namespace="CELERY")
# Descobre tasks em apps registrados (tasks.py)
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    logger.info("Request: %r", self.request)


@app.task(name="escalaconnect.batimento", ignore_result=True)
def batimento(origem="beat"):
    """Batimento do monitor da fila (escalaconnect/monitor_fila.py).

    O beat agenda a cada 5 min (origem 'beat'); o /healthz/celery publica testes (origem 'monitor').
    Fica aqui, no próprio app, para estar sempre registrada no worker.
    """
    from escalaconnect.monitor_fila import registrar_batimento

    registrar_batimento(origem)
