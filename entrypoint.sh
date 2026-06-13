#!/bin/sh
# Entrypoint de produção do Escala Connect.
# Migra, coleta estáticos e sobe o gunicorn. Em script (não no YAML) para evitar
# problemas de quebra de linha/indentação do docker-compose.
set -e

echo "[entrypoint] Aplicando migrações..."
python manage.py migrate --noinput

echo "[entrypoint] Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

echo "[entrypoint] Iniciando gunicorn em 0.0.0.0:8000..."
exec gunicorn escalaconnect.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
