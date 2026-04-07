from datetime import datetime
from app.models.reservation import Reservation
from app.repositories import reservation_repository


def can_cancel(reservation: Reservation) -> bool:
    return reservation.status == 'active' and reservation.start_time > datetime.utcnow()


def cancel(reservation: Reservation) -> None:
    reservation.status = 'cancelled'
    reservation_repository.save(reservation)


def create(user_id: int, table_id: int, order_id: int, start_time: datetime, end_time: datetime) -> Reservation:
    reservation = Reservation(
        user_id=user_id,
        table_id=table_id,
        order_id=order_id,
        start_time=start_time,
        end_time=end_time,
    )
    reservation_repository.save(reservation)
    return reservation
