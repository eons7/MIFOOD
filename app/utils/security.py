"""Декоратор admin_required и audit-логгер."""
from functools import wraps

from flask import abort, current_app, request
from flask_login import current_user


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
