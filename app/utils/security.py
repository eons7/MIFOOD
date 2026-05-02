"""Декоратор admin_required, audit-логгер, валидация паролей."""
import re
from functools import wraps

from flask import abort, current_app, request
from flask_login import current_user

PASSWORD_MIN_LEN = 8


def validate_password(password: str) -> str | None:
    """Возвращает текст ошибки или None, если пароль валиден.
    Требования: не короче 8 символов, минимум одна буква и одна цифра.
    """
    if not password or len(password) < PASSWORD_MIN_LEN:
        return f'Пароль должен быть не короче {PASSWORD_MIN_LEN} символов'
    if not re.search(r'[A-Za-zА-Яа-яЁё]', password):
        return 'Пароль должен содержать хотя бы одну букву'
    if not re.search(r'\d', password):
        return 'Пароль должен содержать хотя бы одну цифру'
    return None


def admin_required(view):
    """Пропускает только аутентифицированных админов (иначе 401/403)."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapper


def audit(action: str, **fields):
    """Пишет в app.logger строку 'AUDIT action=... actor=... ip=... <fields>'."""
    actor = getattr(current_user, 'id', None) if current_user else None
    ip = request.remote_addr if request else None
    parts = [f'{k}={v}' for k, v in fields.items()]
    current_app.logger.info(
        'AUDIT action=%s actor=%s ip=%s %s',
        action, actor, ip, ' '.join(parts),
    )
