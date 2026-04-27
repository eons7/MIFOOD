"""SSE-эндпоинты для real-time обновлений у студента.

Один stream-обработчик на пользователя. События публикуются из админки
после смены статуса (admin.update_order_status) — клиент получает
HTML-фрагмент партиала статуса и Bootstrap-toast'ит.

Подключено: app/__init__.py register_blueprint(sse_bp, url_prefix='/sse').
"""
import json
import queue

from flask import Blueprint, Response, render_template, stream_with_context
from flask_login import login_required, current_user

from app.extensions import csrf
from app.services import pubsub

sse_bp = Blueprint('sse', __name__)


@sse_bp.route('/my-orders')
@login_required
@csrf.exempt
def my_orders_stream():
    """SSE-стрим: события только этого пользователя.

    Шлёт два типа событий:
      - 'order-status' — HTML-партиал статуса (для htmx sse-swap)
      - 'order-ready'  — JSON {order_id, status} (для JS-toast'а)
    """
    user_id = current_user.id

    def gen():
        q = pubsub.subscribe()
        try:
            # Сразу отправим heartbeat чтобы соединение точно открылось
            yield ': connected\n\n'
            while True:
                try:
                    event = q.get(timeout=25)
                except queue.Empty:
                    yield ': keepalive\n\n'
                    continue

                if event.get('user_id') != user_id:
                    continue

                if event.get('type') == 'order-status':
                    # Партиал — для htmx
                    from app.repositories import order_repository
                    order = order_repository.get_by_id(event['order_id'])
                    if order is None:
                        continue
                    html = render_template('orders/_status_block.html', order=order)
                    # SSE-формат: одно событие, многострочный data: с префиксом каждой строки
                    data_lines = '\n'.join('data: ' + line for line in html.splitlines())
                    yield f'event: order-status\n{data_lines}\n\n'

                    # Дополнительно — JSON для тоста (отдельным событием)
                    payload = json.dumps({'order_id': event['order_id'], 'status': event['status']})
                    yield f'event: order-toast\ndata: {payload}\n\n'
        except GeneratorExit:
            pass
        finally:
            pubsub.unsubscribe(q)

    response = Response(stream_with_context(gen()), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    return response
