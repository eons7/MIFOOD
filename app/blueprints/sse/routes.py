"""SSE-эндпоинты. Шлют JSON-сигналы; HTML тянется отдельным HTMX hx-get."""
import json
import queue

from flask import Blueprint, Response, abort, stream_with_context
from flask_login import login_required, current_user

from app.extensions import csrf
from app.services import pubsub

sse_bp = Blueprint('sse', __name__)


def _stream(filter_fn, event_name: str):
    """SSE-генератор. filter_fn(event) → bool, отбирает события для стрима."""
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
    """Стрим событий по заказам текущего студента."""
    user_id = current_user.id
    return _stream(
        filter_fn=lambda e: e.get('user_id') == user_id,
        event_name='my-order-update',
    )


@sse_bp.route('/kds')
@login_required
@csrf.exempt
def kds_stream():
    """Стрим событий KDS для админа: order-status, order-new, reservation-status."""
    if not current_user.is_admin:
        abort(403)
    return _stream(
        filter_fn=lambda e: e.get('type') in (
            'order-status', 'order-new', 'reservation-status',
        ),
        event_name='kds-update',
    )
