from app.extensions import db
from app.models.reservation import Reservation, Table


def get_by_id(reservation_id: int) -> Reservation | None:
    return db.session.get(Reservation, reservation_id)


def get_by_user(user_id: int) -> list[Reservation]:
    return Reservation.query.filter_by(user_id=user_id).order_by(Reservation.start_time.desc()).all()


def has_conflict(table_id: int, start_time, end_time) -> bool:
    return Reservation.query.filter(
        Reservation.table_id == table_id,
        Reservation.status == 'active',
        Reservation.start_time < end_time,
        Reservation.end_time > start_time
    ).first() is not None


def get_available_tables(start_time, end_time) -> list[Table]:
    active_tables = Table.query.filter_by(is_active=True).all()
    return [t for t in active_tables if not has_conflict(t.id, start_time, end_time)]


def save(reservation: Reservation) -> Reservation:
    db.session.add(reservation)
    db.session.commit()
    return reservation
