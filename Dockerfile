FROM python:3.11-slim

WORKDIR /app

# Устанавливаем зависимости системы (нужны для некоторых библиотек)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Копируем pyproject.toml
COPY pyproject.toml .

# Устанавливаем pip и зависимости напрямую (без Poetry)
RUN pip install --no-cache-dir \
    flask>=3.0 \
    flask-sqlalchemy>=3.1 \
    flask-migrate>=4.0 \
    flask-login>=0.6 \
    flask-wtf>=1.2 \
    python-dotenv>=1.0 \
    email-validator>=2.1 \
    Pillow>=10.0

# Копируем весь проект
COPY . .

# Создаём папку для базы данных (если используется SQLite)
RUN mkdir -p /app/instance

# Открываем порт (Flask по умолчанию 5000)
EXPOSE 5000

# Переменные окружения
ENV FLASK_APP=run.py
ENV FLASK_ENV=production

# Запускаем приложение
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
