"""Утилиты безопасности: декоратор admin_required и audit-логгер.

Зачем отдельный модуль:
- admin_required даёт единый way гард для админских ручек (вместо
  ручного check_admin() в каждом view).
- audit() пишет в стандартный app.logger важные действия (смена статуса,
  отмена брони, продление и т.п.) — этого достаточно для academic-проекта,
  без отдельной таблицы в БД.
"""
from functools import wraps

from flask import abort, current_app, request
from flask_login import current_user


def admin_required(view):
    """Допускает только аутентифицированных админов. Иначе 401/403."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapper


def audit(action: str, **fields):
    """Пишет аудит-запись в app.logger (уровень INFO).

    Пример: audit('order.status_change', order_id=42, new='ready')
    В логи попадает: actor, IP, action и переданные поля.
    """
    actor = getattr(current_user, 'id', None) if current_user else None
    ip = request.remote_addr if request else None
    parts = [f'{k}={v}' for k, v in fields.items()]
    current_app.logger.info(
        'AUDIT action=%s actor=%s ip=%s %s',
        action, actor, ip, ' '.join(parts),
    )
