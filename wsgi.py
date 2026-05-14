import os
from app import create_app

app = create_app()


def _apply_migrations():
    """Накатывает alembic-миграции при старте в production."""
    from flask_migrate import upgrade
    with app.app_context():
        try:
            upgrade()
            print("[wsgi] migrations applied", flush=True)
        except Exception as e:
            print(f"[wsgi] migrations skipped: {e}", flush=True)


if __name__ == "__main__":
    is_prod = os.getenv("FLASK_ENV") == "production"
    if is_prod:
        _apply_migrations()

    port = int(os.environ.get("PORT", 5000))
    app.run(
        debug=not is_prod,
        host="0.0.0.0",
        port=port,
        threaded=True,
    )
