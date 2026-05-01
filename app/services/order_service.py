from datetime import timedelta

from app.extensions import db
from app.models.order import Order
from app.repositories import order_repository, reservation_repository
from app.utils.timezones import now_utc_naive

CANCELLABLE_STATUSES = ['pending', 'confirmed']

# Сколько ждём гостя после pickup_time, прежде чем заказ считается «не забран»
EXPIRE_AFTER_MINUTES = 15
# На сколько минут админ может продлить заказ одной кнопкой
EXTEND_MINUTES = 15
# Если до следующей брони на столе осталось меньше — продлевать бессмысленно,
# кнопка прячется
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
    """Помечает готовые заказы, которые гость не забрал в течение
    EXPIRE_AFTER_MINUTES после pickup_time, как 'expired'. Связанная бронь
    автоматически отменяется (если ещё была scheduled/active), чтобы стол
    освободился. Лениво вызывается на страницах списков заказов.
    """
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
    """Кнопка «продлить» нужна только когда есть бронь — иначе продлевать нечего,
    заказ просто не истекает по времени, если двигать pickup_time."""
    if order.status not in ('pending', 'confirmed', 'ready'):
        return False
    if order.reservation is None:
        return False
    if order.reservation.status not in ('scheduled', 'active'):
        return False
    return max_extend_minutes(order) >= MIN_USEFUL_EXTEND_MINUTES


def max_extend_minutes(order: Order) -> int:
    """Максимум минут, на которые можно продлить бронь без коллизии со
    следующей бронью на этом столе. Не больше EXTEND_MINUTES.
    Возвращает 0, если у заказа нет брони.
    """
    r = order.reservation
    if r is None:
        return 0
    next_r = reservation_repository.next_after(r.table_id, r.end_time, exclude_id=r.id)
    if next_r is None:
        return EXTEND_MINUTES
    gap = (next_r.start_time - r.end_time).total_seconds() / 60
    return max(0, min(EXTEND_MINUTES, int(gap)))


def extend(order: Order) -> int:
    """Двигает pickup_time заказа и end_time связанной брони вперёд на
    max_extend_minutes() минут. Возвращает фактическое число минут.
    Серверный capping — даже если кто-то подделает форму, продление
    не залезет в следующую бронь.
    """
    minutes = max_extend_minutes(order)
    if minutes < MIN_USEFUL_EXTEND_MINUTES:
        return 0
    delta = timedelta(minutes=minutes)
    order.pickup_time = order.pickup_time + delta
    if order.reservation:
        order.reservation.end_time = order.reservation.end_time + delta
    db.session.commit()
    return minutes
