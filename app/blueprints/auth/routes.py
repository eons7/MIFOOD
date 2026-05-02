from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import limiter
from app.repositories import user_repository
from app.services import auth_service
from app.utils.security import audit, validate_password

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit('10 per minute', methods=['POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.orders') if current_user.is_admin else url_for('menu.index'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = user_repository.get_by_email(email)
        if user is None or not auth_service.verify_password(user, password):
            audit('auth.login_failed', email=email)
            flash('Неверный email или пароль', 'danger')
            return redirect(url_for('auth.login'))
        # Защита от session fixation: чистим старую анонимную сессию.
        session.clear()
        login_user(user)
        audit('auth.login_ok', user_id=user.id)
        return redirect(url_for('admin.orders') if user.is_admin else url_for('menu.index'))
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit('5 per minute', methods=['POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('menu.index'))
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        password2 = request.form.get('password_confirm')
        if password != password2:
            flash('Пароли не совпадают', 'danger')
            return redirect(url_for('auth.register'))
        pwd_error = validate_password(password)
        if pwd_error:
            flash(pwd_error, 'danger')
            return redirect(url_for('auth.register'))
        if user_repository.exists_by_email(email):
            flash('Email уже занят', 'danger')
            return redirect(url_for('auth.register'))
        new_user = auth_service.register(name=name, email=email, password=password)
        audit('auth.register', user_id=new_user.id, email=email)
        flash('Регистрация успешна! Войдите в систему.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html')

@auth_bp.route('/logout', methods=['GET'])
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('auth.login'))
