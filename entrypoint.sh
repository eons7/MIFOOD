#!/bin/sh
set -e

echo "[entrypoint] running flask db upgrade"
flask db upgrade

PORT="${PORT:-5000}"
WORKERS="${GUNICORN_WORKERS:-1}"
THREADS="${GUNICORN_THREADS:-8}"

echo "[entrypoint] starting gunicorn on 0.0.0.0:${PORT} workers=${WORKERS} threads=${THREADS}"
exec gunicorn \
    --bind "0.0.0.0:${PORT}" \
    --workers "${WORKERS}" \
    --threads "${THREADS}" \
    --worker-class gthread \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    "run:app"
