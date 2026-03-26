def test_models_use_single_db_instance():
    from app.extensions import db
    from app.models.menu import Category, MenuItem
    from app.models.order import Order, OrderItem
    from app.models.reservation import Reservation, Table
    from app.models.user import User

    # Модели должны быть объявлены через тот же db, что и приложение.
    assert Category.metadata is db.Model.metadata
    assert MenuItem.metadata is db.Model.metadata
    assert Order.metadata is db.Model.metadata
    assert OrderItem.metadata is db.Model.metadata
    assert Reservation.metadata is db.Model.metadata
    assert Table.metadata is db.Model.metadata
    assert User.metadata is db.Model.metadata


def test_expected_tables_are_registered_in_metadata():
    # Важно: импортируем все модели до проверки metadata.tables,
    # иначе таблицы могут не быть зарегистрированы.
    from app.extensions import db
    from app.models import menu, order, reservation, user  # noqa: F401

    expected = {
        "users",
        "categories",
        "menu_items",
        "orders",
        "order_items",
        "tables",
        "reservations",
    }
    assert expected.issubset(set(db.Model.metadata.tables.keys()))
