from datetime import datetime
from app.extensions import db
from app.models.reservation import Reservation
from app.repositories import reservation_repository
from app.services import pubsub
from app.utils.timezones import now_utc_naive


def _publish(reservation: Reservation) -> None:
    """Публикует событие смены статуса брони в pubsub."""
    pubsub.publish({
        'type': 'reservation-status',
        'reservation_id': reservation.id,
        'status': reservation.status,
        'user_id': reservation.user_id,
    })


def complete_expired() -> int:
    """scheduled/active с истёкшим end_time → completed. Возвращает кол-во записей."""
    now = now_utc_naive()
    expired = Reservation.query.filter(
        Reservation.status.in_(('scheduled', 'active')),
        Reservation.end_time < now,
    ).all()
    for r in expired:
        r.status = 'completed'
    if expired:
        db.session.commit()
        for r in expired:
            _publish(r)
    return len(expired)


def can_cancel(reservation: Reservation) -> bool:
    """Отменить можно только бронь со статусом 'scheduled'."""
    return reservation.status == 'scheduled'


def cancel(reservation: Reservation) -> None:
    reservation.status = 'cancelled'
    reservation_repository.save(reservation)
    _publish(reservation)


def create(user_id: int, table_id: int, order_id: int, start_time: datetime, end_time: datetime) -> Reservation:
    """Создаёт бронь со статусом 'scheduled'."""
    reservation = Reservation(
        user_id=user_id,
        table_id=table_id,
        order_id=order_id,
        start_time=start_time,
        end_time=end_time,
        status='scheduled',
    )
    reservation_repository.save(reservation)
    return reservation


def activate_started() -> int:
    """scheduled с start_time<=now<end_time → active. Возвращает кол-во записей."""
    now = now_utc_naive()
    rows = Reservation.query.filter(
        Reservation.status == 'scheduled',
        Reservation.start_time <= now,
        Reservation.end_time > now,
    ).all()
    for r in rows:
        r.status = 'active'
    if rows:
        db.session.commit()
        for r in rows:
            _publish(r)
    return len(rows)
