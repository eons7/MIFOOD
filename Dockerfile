FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY app/ ./app/

# Рантайм + prod-extras (psycopg2, gunicorn) из pyproject.toml
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir ".[prod]"

COPY . .

RUN mkdir -p /app/instance

EXPOSE 5000

ENV FLASK_APP=wsgi \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN chmod +x /app/scripts/entrypoint.sh

CMD ["/app/scripts/entrypoint.sh"]
