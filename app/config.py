import os
from dotenv import load_dotenv
from sqlalchemy.engine.url import URL

load_dotenv()


def _build_db_uri() -> str | None:
    """Источники в порядке приоритета:
    1) DB_HOST + DB_USER + DB_PASSWORD + DB_NAME (+ DB_PORT) — собирает URL через URL.create.
    2) DATABASE_URL — берётся как есть, нормализуется к postgresql+psycopg2.
    """
    host = os.getenv("DB_HOST")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    name = os.getenv("DB_NAME")
    if host and user and name:
        port = int(os.getenv("DB_PORT", "5432"))
        return URL.create(
            drivername="postgresql+psycopg2",
            username=user,
            password=password or None,
            host=host,
            port=port,
            database=name,
        ).render_as_string(hide_password=False)

    url = os.getenv("DATABASE_URL")
    if not url:
        return None
    if url.startswith("postgres://"):
        url = "postgresql+psycopg2://" + url[len("postgres://"):]
    elif url.startswith("postgresql://") and "+psycopg2" not in url:
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-замени!")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_TIME_LIMIT = None  # токен живёт всю сессию

    # ЮKassa: тестовый префикс ключа `test_`, боевой `live_`. Если не задано —
    # онлайн-оплата отключена (кнопка не показывается).
    YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
    YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = _build_db_uri() or "sqlite:///mifud_dev.db"


class ProductionConfig(BaseConfig):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = _build_db_uri()

    # Cookie/CSRF только по HTTPS
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    WTF_CSRF_SSL_STRICT = True
    PREFERRED_URL_SCHEME = "https"


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


config = {
    "development": DevelopmentConfig,
    "production":  ProductionConfig,
    "testing":     TestingConfig,
    "default":     DevelopmentConfig,
}
