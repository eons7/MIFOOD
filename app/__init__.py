from flask import Flask, render_template
from .extensions import db, migrate, login_manager
from .config import config


def create_app(config_name="development"):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    @app.get("/")
    def home():
        # В проекте blueprint-роуты пока не реализованы, поэтому даём
        # стартовую страницу, чтобы можно было увидеть базовую верстку.
        return render_template("home.html")

    # Подключение расширений
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id: str):
        # Минимальная реализация, чтобы шаблоны с current_user работали.
        # Модели/роуты будут дополняться позже.
        try:
            from app.models.user import User
        except Exception:
            return None
        try:
            return User.query.get(int(user_id))
        except Exception:
            return None

    # Регистрация blueprint'ов (модулей сайта)
    from .blueprints.auth         import auth_bp
    from .blueprints.menu         import menu_bp
    from .blueprints.orders       import orders_bp
    from .blueprints.reservations import reservations_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(menu_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(reservations_bp)

    return app
