import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id           = db.Column(db.Integer,     primary_key=True)
    name         = db.Column(db.String(100), nullable=False)
    email        = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin     = db.Column(db.Boolean,     default=False)
    created_at   = db.Column(db.DateTime,    default=datetime.utcnow)

    #Связи
    orders       = db.relationship('Order',       backref='student', lazy=True)
    reservations = db.relationship('Reservation', backref='student', lazy=True)

    def __repr__(self):
        return f'<User {self.email}>'
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)