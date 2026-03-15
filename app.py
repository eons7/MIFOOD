from flask import Flask
from extensions import db

# Импортируем все модели чтобы SQLAlchemy знал о них при db.create_all()
from models.user import User
from models.menu import Category, MenuItem
from models.order import Order, OrderItem
from models.reservation import Table, Reservation


def create_app():
    app = Flask(__name__)

    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///canteen.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = '54'

    db.init_app(app)

    with app.app_context():
        db.create_all()  # Создаёт все таблицы если их ещё нет
        print('✅ База данных создана')

    return app
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
