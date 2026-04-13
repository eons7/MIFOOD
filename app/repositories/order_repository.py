from app.extensions import db
from app.models.order import Order, OrderItem

ACTIVE_STATUSES = ['pending', 'confirmed', 'ready']


def get_by_id(order_id: int) -> Order | None:
    return db.session.get(Order, order_id)


def get_by_user(user_id: int) -> list[Order]:
    return Order.query.filter_by(user_id=user_id).order_by(Order.created_at.desc()).all()


def get_active_count(user_id: int) -> int:
    return Order.query.filter(
        Order.user_id == user_id,
        Order.status.in_(ACTIVE_STATUSES)
    ).count()


def save(order: Order) -> Order:
    db.session.add(order)
    db.session.commit()
    return order


def delete(order: Order) -> None:
    db.session.delete(order)
    db.session.commit()
