import os
import re

from flask import Flask, make_response
from werkzeug.middleware.proxy_fix import ProxyFix

from app.utils.timezones import format_local

from app.extensions import db, migrate, login_manager, csrf, talisman, limiter
from app.config import config as config_map

_SIZE_SUFFIX_RE = re.compile(r'^(.+)_([SML])$')


def pretty_name(name: str | None) -> str:
    """«Капучино_L» → «Капучино (L)»."""
    if not name:
        return ''
    m = _SIZE_SUFFIX_RE.match(name)
    return f"{m.group(1)} ({m.group(2)})" if m else name


def create_app(config_name: str | None = None):
    app = Flask(__name__)
    config_name = config_name or os.getenv('FLASK_ENV', 'default')
    app.config.from_object(config_map.get(config_name, config_map['default']))

    # ProxyFix включается только за реальным обратным прокси (production).
    if config_name == 'production':
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Security headers: CSP, HSTS, X-Frame, Referrer-Policy.
    is_prod = (config_name == 'production')
    csp = {
        'default-src': "'self'",
        'script-src': [
            "'self'",
            "'unsafe-inline'",
            'https://cdn.jsdelivr.net',
            'https://unpkg.com',
        ],
        'style-src': [
            "'self'",
            "'unsafe-inline'",
            'https://cdn.jsdelivr.net',
        ],
        'img-src': ["'self'", 'data:', 'blob:'],
        'font-src': ["'self'", 'https://cdn.jsdelivr.net', 'data:'],
        'connect-src': ["'self'"],
        'frame-ancestors': "'none'",
        'base-uri': "'self'",
    }
    talisman.init_app(
        app,
        force_https=is_prod,
        strict_transport_security=is_prod,
        session_cookie_secure=is_prod,
        content_security_policy=csp,
        content_security_policy_nonce_in=[],
        referrer_policy='strict-origin-when-cross-origin',
        frame_options='DENY',
    )

    limiter.init_app(app)

    app.jinja_env.filters['pretty_name'] = pretty_name
    app.jinja_env.filters['local_dt'] = format_local

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
