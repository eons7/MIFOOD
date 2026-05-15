#!/bin/sh
# entrypoint: миграции + запуск gunicorn

set -u
cd /app

# FLASK_APP жёстко переопределяем — игнорируем внешние env vars с возможными пробелами
unset FLASK_APP
export FLASK_APP=wsgi

echo "[entrypoint] running 'python -m flask db upgrade' (FLASK_APP=wsgi)"
if python -m flask db upgrade; then
    echo "[entrypoint] migrations OK"
else
    echo "[entrypoint] WARN: migrations failed, starting gunicorn anyway"
fi

PORT="${PORT:-5000}"
WORKERS="${GUNICORN_WORKERS:-1}"
THREADS="${GUNICORN_THREADS:-32}"

echo "[entrypoint] starting gunicorn on 0.0.0.0:${PORT} workers=${WORKERS} threads=${THREADS}"
exec gunicorn \
    --bind "0.0.0.0:${PORT}" \
    --workers "${WORKERS}" \
    --threads "${THREADS}" \
    --worker-class gthread \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    "wsgi:app"
