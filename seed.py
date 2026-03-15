from app import create_app
from extensions import db
from models.user import User
from models.menu import Category, MenuItem

app = create_app()

with app.app_context():
    # Добавляем категорию
    cat1 = Category(name='Первые блюда')
    cat2 = Category(name='Напитки')
    db.session.add(cat1)
    db.session.add(cat2)
    db.session.commit()

    # Добавляем блюда
    item1 = MenuItem(name='Борщ', price=120.0, category_id=cat1.id)
    item2 = MenuItem(name='Чай', price=30.0, category_id=cat2.id)
    db.session.add(item1)
    db.session.add(item2)
    db.session.commit()

    # Добавляем пользователя
    user = User(name='Максим', email='max@mail.ru', password_hash='хэш_пароля')
    db.session.add(user)
    db.session.commit()

    print('✅ Данные добавлены!')