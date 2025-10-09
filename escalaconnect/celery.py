import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "escalaconnect.settings")

app = Celery("escalaconnect")
# Puxa configurações prefixadas com CELERY_ do settings
app.config_from_object("django.conf:settings", namespace="CELERY")
# Descobre tasks em apps registrados (tasks.py)
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
