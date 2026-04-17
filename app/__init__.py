from flask import Flask, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

import os

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'

@app.route('/sw.js')
def service_worker():
    response = make_response(app.send_static_file('sw.js'))
    response.headers['Content-Type'] = 'application/javascript'
    response.headers['Service-Worker-Allowed'] = '/'
    return response

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Регистрация blueprints
    from app.blueprints.auth.routes import auth_bp
    from app.blueprints.menu.routes import menu_bp
    from app.blueprints.orders.routes import orders_bp
    from app.blueprints.reservations.routes import reservations_bp
    from app.blueprints.admin.routes import admin_bp

    app.register_blueprint(auth_bp,         url_prefix='/auth')
    app.register_blueprint(menu_bp,         url_prefix='/menu')
    app.register_blueprint(orders_bp,       url_prefix='/orders')
    app.register_blueprint(reservations_bp, url_prefix='/reservations')
    app.register_blueprint(admin_bp,        url_prefix='/admin')

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