"""In-memory pub/sub шина для SSE.

Простая реализация без внешних брокеров — для одного процесса Flask dev-сервера.
Каждый подписчик получает свою Queue, события рассылаются всем.

Использование:
    pubsub.publish({'type': 'order-status', 'order_id': 42, 'status': 'ready', 'user_id': 7})

В SSE-обработчике:
    q = pubsub.subscribe()
    try:
        while True:
            event = q.get(timeout=25)
            yield format_sse(event)
    except GeneratorExit:
        pubsub.unsubscribe(q)
"""
import queue
import threading

_subscribers: list[queue.Queue] = []
_lock = threading.Lock()


def subscribe() -> queue.Queue:
    q: queue.Queue = queue.Queue(maxsize=100)
    with _lock:
        _subscribers.append(q)
    return q


def unsubscribe(q: queue.Queue) -> None:
    with _lock:
        try:
            _subscribers.remove(q)
        except ValueError:
            pass


def publish(event: dict) -> None:
    """Рассылает событие всем подписчикам. Не блокирует — если очередь заполнена, событие теряется."""
    with _lock:
        subs = list(_subscribers)
    for q in subs:
        try:
            q.put_nowait(event)
        except queue.Full:
            pass
