from datetime import datetime
from app.extensions import db


class Table(db.Model):
    __tablename__ = 'tables'

    id        = db.Column(db.Integer, primary_key=True)
    number    = db.Column(db.Integer, nullable=False, unique=True)
    seats     = db.Column(db.Integer, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    #Связи :
    reservations = db.relationship('Reservation', backref='table', lazy=True)
    
    def __repr__(self):
        return f'<Table №{self.number} ({self.seats} мест)>'
    
    @classmethod
    def get_available(cls, pickup_time, duration):
        all_table = Table.query.filter_by(is_active=True).all()
        available = []
        for table in all_table:
            end_time = pickup_time + duration
            if not Reservation.is_conflicting(table.id, pickup_time, end_time):
                available.append(table)
        return available
    
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
    
    @classmethod
    def is_conflicting(cls, table_id, start_time, end_time):
        return Reservation.query.filter(
            Reservation.table_id == table_id,
            Reservation.status == 'active',
            Reservation.start_time < end_time,
            Reservation.end_time > start_time
        ).first() is not None
        
    def is_cancellable(self):
        return self.status == 'active' and self.start_time > datetime.utcnow()
