from datetime import timedelta

from app.extensions import db
from app.models.order import Order
from app.repositories import order_repository, reservation_repository
from app.utils.timezones import now_utc_naive

CANCELLABLE_STATUSES = ['pending', 'confirmed']

# Окно ожидания после pickup_time перед переводом в 'expired' (минут).
EXPIRE_AFTER_MINUTES = 15
# Шаг продления заказа админом (минут).
EXTEND_MINUTES = 15
# Минимальный полезный шаг продления; ниже — кнопка скрывается.
MIN_USEFUL_EXTEND_MINUTES = 5


def calculate_total(order: Order) -> float:
    total = sum(item.quantity * item.menu_item.price for item in order.order_items)
    order.total_price = total
    return total


def can_cancel(order: Order) -> bool:
    return order.status in CANCELLABLE_STATUSES


def cancel(order: Order) -> None:
    order.status = 'cancelled'
    order_repository.save(order)


def expire_overdue() -> int:
    """ready заказы старше EXPIRE_AFTER_MINUTES → expired; связанная бронь → cancelled."""
    now = now_utc_naive()
    threshold = now - timedelta(minutes=EXPIRE_AFTER_MINUTES)
    overdue = Order.query.filter(
        Order.status == 'ready',
        Order.pickup_time < threshold,
    ).all()
    for order in overdue:
        order.status = 'expired'
        if order.reservation and order.reservation.status in ('scheduled', 'active'):
            order.reservation.status = 'cancelled'
    if overdue:
        db.session.commit()
    return len(overdue)


def can_extend(order: Order) -> bool:
    """True, если у заказа есть активная бронь и есть запас минимум MIN_USEFUL_EXTEND_MINUTES."""
    if order.status not in ('pending', 'confirmed', 'ready'):
        return False
    if order.reservation is None:
        return False
    if order.reservation.status not in ('scheduled', 'active'):
        return False
    return max_extend_minutes(order) >= MIN_USEFUL_EXTEND_MINUTES


def max_extend_minutes(order: Order) -> int:
    """Максимум минут продления без коллизии со следующей бронью. Cap = EXTEND_MINUTES."""
    r = order.reservation
    if r is None:
        return 0
    next_r = reservation_repository.next_after(r.table_id, r.end_time, exclude_id=r.id)
    if next_r is None:
        return EXTEND_MINUTES
    gap = (next_r.start_time - r.end_time).total_seconds() / 60
    return max(0, min(EXTEND_MINUTES, int(gap)))


def extend(order: Order) -> int:
    """Двигает pickup_time и end_time брони на max_extend_minutes(). Возвращает применённые минуты."""
    minutes = max_extend_minutes(order)
    if minutes < MIN_USEFUL_EXTEND_MINUTES:
        return 0
    delta = timedelta(minutes=minutes)
    order.pickup_time = order.pickup_time + delta
    if order.reservation:
        order.reservation.end_time = order.reservation.end_time + delta
    db.session.commit()
    return minutes
