from flask import Flask
from .extensions import db, migrate, login_manager
from .config import config


def create_app(config_name="development"):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Подключение расширений
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

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
