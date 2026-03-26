import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from extensions import db


class Order(db.Model):
    __tablename__ = 'orders'

    id          = db.Column(db.Integer,  primary_key=True)
    user_id     = db.Column(db.Integer,  db.ForeignKey('users.id'), nullable=False)
    pickup_time = db.Column(db.DateTime, nullable=False)
    created_at  = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status      = db.Column(db.String(20), nullable=False, default='pending')
    # Возможные значения status:
    # pending   — ожидает подтверждения
    # confirmed — принят в работу
    # ready     — готов к выдаче
    # completed — получен студентом
    # cancelled — отменён
    total_price = db.Column(db.Float,  nullable=False, default=0.0)
    comment     = db.Column(db.Text,   nullable=True)

    # Связи
    order_items = db.relationship(
        'OrderItem',
        backref='order',
        lazy=True,
        cascade='all, delete-orphan'  # при удалении заказа удаляются все его позиции
    )
    reservation = db.relationship('Reservation', backref='order', uselist=False, lazy=True)

    def calculate_total(self):
        """Пересчитывает итоговую сумму по всем позициям заказа."""
        self.total_price = sum(
            item.quantity * item.menu_item.price
            for item in self.order_items
        )
    def is_cancellable(self):
        return self.status in ['pending', 'confirmed']
    @classmethod
    def get_active_count(cls, user_id):
        return Order.query.filter(
            Order.user_id == user_id,
            Order.status.in_(['pending', 'confirmed', 'ready'])
        ).count()

     

    def __repr__(self):
        return f'<Order #{self.id} [{self.status}]>'


class OrderItem(db.Model):
    __tablename__ = 'order_items'

    id           = db.Column(db.Integer, primary_key=True)
    order_id     = db.Column(db.Integer, db.ForeignKey('orders.id'),     nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    quantity     = db.Column(db.Integer, nullable=False, default=1)
    
    def get_subtotal(self):
        return self.menu_item.price * self.quantity
        
    def __repr__(self):
        return f'<OrderItem order={self.order_id} item={self.menu_item_id} x{self.quantity}>'
