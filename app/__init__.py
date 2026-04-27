import os
import re

from flask import Flask, make_response

from app.extensions import db, migrate, login_manager, csrf
from app.config import config as config_map

_SIZE_SUFFIX_RE = re.compile(r'^(.+)_([SML])$')


def pretty_name(name: str | None) -> str:
    """Убирает суффикс размера: «Капучино_L» → «Капучино (L)»."""
    if not name:
        return ''
    m = _SIZE_SUFFIX_RE.match(name)
    return f"{m.group(1)} ({m.group(2)})" if m else name


def create_app(config_name: str | None = None):
    app = Flask(__name__)
    config_name = config_name or os.getenv('FLASK_ENV', 'default')
    app.config.from_object(config_map.get(config_name, config_map['default']))

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    app.jinja_env.filters['pretty_name'] = pretty_name

    # Регистрация blueprints
    from app.blueprints.auth.routes import auth_bp
    from app.blueprints.menu.routes import menu_bp
    from app.blueprints.orders.routes import orders_bp
    from app.blueprints.reservations.routes import reservations_bp
    from app.blueprints.admin.routes import admin_bp
    from app.blueprints.sse.routes import sse_bp

    app.register_blueprint(auth_bp,         url_prefix='/auth')
    app.register_blueprint(menu_bp,         url_prefix='/menu')
    app.register_blueprint(orders_bp,       url_prefix='/orders')
    app.register_blueprint(reservations_bp, url_prefix='/reservations')
    app.register_blueprint(admin_bp,        url_prefix='/admin')
    app.register_blueprint(sse_bp,          url_prefix='/sse')

    @app.route('/')
    def root():
        from flask import redirect, url_for
        from flask_login import current_user
        if current_user.is_authenticated and current_user.is_admin:
            return redirect(url_for('admin.orders'))
        return redirect(url_for('menu.index'))

    @app.route('/sw.js')
    def service_worker():
        response = make_response(app.send_static_file('sw.js'))
        response.headers['Content-Type'] = 'application/javascript'
        response.headers['Service-Worker-Allowed'] = '/'
        return response

    return app


@login_manager.user_loader
def load_user(user_id):
    from app.models.user import User
    return User.query.get(int(user_id))
