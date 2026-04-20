from datetime import datetime
from app.extensions import db


class Table(db.Model):
    __tablename__ = 'tables'

    id        = db.Column(db.Integer, primary_key=True)
    number    = db.Column(db.Integer, nullable=False, unique=True)
    seats     = db.Column(db.Integer, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    reservations = db.relationship('Reservation', backref='table', lazy=True)

    def __repr__(self):
        return f'<Table №{self.number} ({self.seats} мест)>'


class Reservation(db.Model):
    __tablename__ = 'reservations'

    id         = db.Column(db.Integer,    primary_key=True)
    user_id    = db.Column(db.Integer,    db.ForeignKey('users.id'),  nullable=False)
    table_id   = db.Column(db.Integer,    db.ForeignKey('tables.id'), nullable=False)
    order_id   = db.Column(db.Integer,    db.ForeignKey('orders.id'), nullable=False)
    start_time = db.Column(db.DateTime,   nullable=False)
    end_time   = db.Column(db.DateTime,   nullable=False)
    status     = db.Column(db.String(20), nullable=False, default='active')
    # Возможные значения status:
    # active    — действующая бронь
    # cancelled — отменена
    # completed — завершена
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<Reservation user={self.user_id} table={self.table_id} [{self.status}]>'
