"""SSE-эндпоинты для real-time обновлений.

Принцип: SSE шлёт только короткие JSON-сигналы, HTML на клиент приходит
через обычный HTMX hx-get на партиал. Так мы не зависим от SQLAlchemy-сессии
внутри стримящего генератора (там она уже может быть закрыта).

Два потока:
  - /sse/my-orders — студенту: события только по его заказам
  - /sse/kds       — админу: любые order-events (новые, смена статуса)

Подписчик публикует через app.services.pubsub.publish(event), event = dict
с полями {type, order_id, status?, user_id}.
"""
import json
import queue

from flask import Blueprint, Response, abort, stream_with_context
from flask_login import login_required, current_user

from app.extensions import csrf
from app.services import pubsub

sse_bp = Blueprint('sse', __name__)


def _stream(filter_fn, event_name: str):
    """Общий SSE-генератор. filter_fn(event) → bool: пропустить событие или нет."""
    def gen():
        q = pubsub.subscribe()
        try:
            yield ': connected\n\n'
            while True:
                try:
                    event = q.get(timeout=25)
                except queue.Empty:
                    yield ': keepalive\n\n'
                    continue
                if not filter_fn(event):
                    continue
                payload = json.dumps({
                    'type': event.get('type'),
                    'order_id': event.get('order_id'),
                    'status': event.get('status'),
                })
                yield f'event: {event_name}\ndata: {payload}\n\n'
        except GeneratorExit:
            pass
        finally:
            pubsub.unsubscribe(q)

    response = Response(stream_with_context(gen()), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    return response


@sse_bp.route('/my-orders')
@login_required
@csrf.exempt
def my_orders_stream():
    """Студенту — только его заказы."""
    user_id = current_user.id
    return _stream(
        filter_fn=lambda e: e.get('user_id') == user_id,
        event_name='my-order-update',
    )


@sse_bp.route('/kds')
@login_required
@csrf.exempt
def kds_stream():
    """Админу (KDS) — любые события по заказам: новые и смена статуса."""
    if not current_user.is_admin:
        abort(403)
    return _stream(
        filter_fn=lambda e: e.get('type') in (
            'order-status', 'order-new', 'reservation-status',
        ),
        event_name='kds-update',
    )
