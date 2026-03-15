import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from extensions import db


class Table(db.Model):
    __tablename__ = 'tables'

    id        = db.Column(db.Integer, primary_key=True)
    number    = db.Column(db.Integer, nullable=False, unique=True)
    seats     = db.Column(db.Integer, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    # Связи
    reservations = db.relationship('Reservation', backref='table', lazy=True)

    def __repr__(self):
        return f'<Table №{self.number} ({self.seats} мест)>'


class Reservation(db.Model):
    __tablename__ = 'reservations'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'),  nullable=False)
    table_id   = db.Column(db.Integer, db.ForeignKey('tables.id'), nullable=False)
    order_id   = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)  # NOT NULL — бронь только при заказе
    start_time = db.Column(db.DateTime, nullable=False)
    end_time   = db.Column(db.DateTime, nullable=False)  # start_time + длительность
    status     = db.Column(db.String(20), nullable=False, default='active')
    # Возможные значения status:
    # active    — действующая бронь
    # cancelled — отменена
    # completed — завершена
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<Reservation user={self.user_id} table={self.table_id} [{self.status}]>'
