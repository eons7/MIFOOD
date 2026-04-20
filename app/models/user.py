from datetime import datetime
from app.extensions import db
from flask_login import UserMixin


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id            = db.Column(db.Integer,     primary_key=True)
    name          = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin      = db.Column(db.Boolean,     default=False)
    created_at    = db.Column(db.DateTime,    default=datetime.utcnow)

    orders       = db.relationship('Order',       backref='student', lazy=True)
    reservations = db.relationship('Reservation', backref='student', lazy=True)

    def __repr__(self):
        return f'<User {self.email}>'
