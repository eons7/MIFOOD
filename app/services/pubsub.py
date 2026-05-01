"""In-memory pub/sub шина для SSE. Один процесс, без внешних брокеров."""
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
    """Рассылает событие всем подписчикам. Не блокирует, при переполнении событие теряется."""
    with _lock:
        subs = list(_subscribers)
    for q in subs:
        try:
            q.put_nowait(event)
        except queue.Full:
            pass
