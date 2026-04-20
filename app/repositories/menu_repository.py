from app.extensions import db
from app.models.menu import Category, MenuItem


def get_all_categories() -> list[Category]:
    return Category.query.order_by(Category.name).all()


def get_all_items() -> list[MenuItem]:
    return MenuItem.query.order_by(MenuItem.category_id, MenuItem.name).all()


def get_available_items() -> list[MenuItem]:
    return MenuItem.query.filter_by(is_available=True).order_by(MenuItem.category_id, MenuItem.name).all()


def get_item_by_id(item_id: int) -> MenuItem | None:
    return db.session.get(MenuItem, item_id)


def save_item(item: MenuItem) -> MenuItem:
    db.session.add(item)
    db.session.commit()
    return item
