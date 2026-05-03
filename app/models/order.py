from app.extensions import db
from app.utils.timezones import now_utc_naive


class Order(db.Model):
    __tablename__ = 'orders'

    id          = db.Column(db.Integer,    primary_key=True)
    user_id     = db.Column(db.Integer,    db.ForeignKey('users.id'), nullable=False)
    pickup_time = db.Column(db.DateTime,   nullable=False)
    created_at  = db.Column(db.DateTime,   nullable=False, default=now_utc_naive)
    status      = db.Column(db.String(20), nullable=False, default='pending')
    # Кухонный FSM:
    # pending   — ожидает подтверждения
    # confirmed — принят в работу
    # ready     — готов к выдаче
    # completed — получен студентом
    # cancelled — отменён
    # expired   — не забран в течение 15 мин с pickup_time
    is_paid     = db.Column(db.Boolean, nullable=False, default=False)
    # is_paid — независимая ось: оплата онлайн или налом при выдаче.
    # Ставится True по двум путям:
    #   1) студент жмёт «Оплатить онлайн» → /orders/<id>/pay
    #   2) админ переводит заказ в completed → считаем, что нал получен
    total_price = db.Column(db.Float, nullable=False, default=0.0)
    comment     = db.Column(db.Text,  nullable=True)
    # ID платежа в ЮKassa. None если оплата онлайн не инициирована.
    payment_id  = db.Column(db.String(64), nullable=True, index=True)

    order_items = db.relationship(
        'OrderItem',
        backref='order',
        lazy=True,
        cascade='all, delete-orphan'
    )
    reservation = db.relationship('Reservation', backref='order', uselist=False, lazy=True)

    def __repr__(self):
        return f'<Order #{self.id} [{self.status}]>'


class OrderItem(db.Model):
    __tablename__ = 'order_items'

    id           = db.Column(db.Integer, primary_key=True)
    order_id     = db.Column(db.Integer, db.ForeignKey('orders.id'),     nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    quantity     = db.Column(db.Integer, nullable=False, default=1)

    def __repr__(self):
        return f'<OrderItem order={self.order_id} item={self.menu_item_id} x{self.quantity}>'
