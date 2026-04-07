"""
Временный blueprint для просмотра всех страниц без бэкенд-логики.
Удалить после реализации настоящих routes.

Запуск: flask run → http://127.0.0.1:5000/preview/
"""

from datetime import datetime, timedelta
from flask import Blueprint, render_template, request

preview_bp = Blueprint('preview', __name__, url_prefix='/preview')


# ── Фейковые объекты для шаблонов ──────────────────────────────────

class Obj:
    """Простой объект-заглушка: принимает любые поля через kwargs."""
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)

    def __getattr__(self, name):
        return None

    def strftime(self, fmt):
        return self  # на случай если шаблон вызовет .strftime на None


# Категории
cats = [
    Obj(id=1, name='Первые блюда'),
    Obj(id=2, name='Вторые блюда'),
    Obj(id=3, name='Напитки'),
    Obj(id=4, name='Салаты'),
    Obj(id=5, name='Выпечка'),
]

# Блюда
menu_items = [
    Obj(id=1, name='Борщ украинский', description='С говядиной и сметаной',
        price=89, image_url=None, is_available=True, category=cats[0], category_id=1),
    Obj(id=2, name='Котлета с гречкой', description='Домашняя котлета, гречневая каша',
        price=120, image_url=None, is_available=True, category=cats[1], category_id=2),
    Obj(id=3, name='Компот из сухофруктов', description='Яблоко, груша, изюм',
        price=35, image_url=None, is_available=True, category=cats[2], category_id=3),
    Obj(id=4, name='Салат Оливье', description='Классический рецепт',
        price=75, image_url=None, is_available=True, category=cats[3], category_id=4),
    Obj(id=5, name='Пирожок с капустой', description=None,
        price=45, image_url=None, is_available=False, category=cats[4], category_id=5),
]

now = datetime.now()

# Позиции заказа
order_items = [
    Obj(id=1, menu_item=menu_items[0], quantity=1, order_id=42, menu_item_id=1),
    Obj(id=2, menu_item=menu_items[1], quantity=1, order_id=42, menu_item_id=2),
    Obj(id=3, menu_item=menu_items[2], quantity=2, order_id=42, menu_item_id=3),
]

# Заказ
order = Obj(
    id=42,
    user_id=1,
    status='pending',
    pickup_time=now.replace(hour=13, minute=30, second=0),
    created_at=now.replace(hour=12, minute=15, second=0),
    total_price=279,
    comment='',
    order_items=order_items,
)

# Столы
tables = [Obj(id=i, number=i, seats=4 if i % 2 == 0 else 2, is_active=True) for i in range(1, 9)]

table_statuses = {
    1: 'busy',
    2: 'free',
    3: 'selected',
    4: 'free',
    5: 'free',
    6: 'busy',
    7: 'closed',
    8: 'free',
}

# Брони
reservations = [
    Obj(id=1, user_id=1, table=tables[2], table_id=3, order_id=42, status='active',
        start_time=now.replace(hour=13, minute=30), end_time=now.replace(hour=14, minute=30)),
    Obj(id=2, user_id=1, table=tables[0], table_id=1, order_id=45, status='active',
        start_time=(now + timedelta(days=1)).replace(hour=12, minute=0),
        end_time=(now + timedelta(days=1)).replace(hour=12, minute=30)),
    Obj(id=3, user_id=1, table=tables[1], table_id=2, order_id=39, status='completed',
        start_time=(now - timedelta(days=1)).replace(hour=12, minute=0),
        end_time=(now - timedelta(days=1)).replace(hour=12, minute=30)),
    Obj(id=4, user_id=1, table=tables[3], table_id=4, order_id=35, status='cancelled',
        start_time=(now - timedelta(days=2)).replace(hour=12, minute=30),
        end_time=(now - timedelta(days=2)).replace(hour=13, minute=0)),
]

# Несколько заказов для админки
admin_orders = [
    Obj(id=42, status='pending', pickup_time=now.replace(hour=13, minute=30),
        created_at=now, total_price=279, order_items=order_items),
    Obj(id=41, status='pending', pickup_time=now.replace(hour=13, minute=45),
        created_at=now, total_price=110,
        order_items=[Obj(menu_item=menu_items[2], quantity=1), Obj(menu_item=menu_items[0], quantity=1)]),
    Obj(id=40, status='confirmed', pickup_time=now.replace(hour=13, minute=0),
        created_at=now, total_price=195,
        order_items=[Obj(menu_item=menu_items[3], quantity=1), Obj(menu_item=menu_items[1], quantity=1)]),
    Obj(id=39, status='confirmed', pickup_time=now.replace(hour=12, minute=30),
        created_at=now, total_price=134,
        order_items=[Obj(menu_item=menu_items[0], quantity=1), Obj(menu_item=menu_items[4], quantity=1)]),
    Obj(id=38, status='ready', pickup_time=now.replace(hour=12, minute=0),
        created_at=now, total_price=110,
        order_items=[Obj(menu_item=menu_items[2], quantity=1), Obj(menu_item=menu_items[0], quantity=1)]),
]


# ── Фейковый current_user для шаблонов ─────────────────────────────

class FakeUser:
    is_authenticated = True
    is_admin = False
    name = 'ИВАН'

class FakeAdmin:
    is_authenticated = True
    is_admin = True
    name = 'ADMIN'


# ── Роуты превью ───────────────────────────────────────────────────

@preview_bp.get('/')
def index():
    return render_template('preview_index.html')


@preview_bp.get('/login')
def login():
    return render_template('auth/login.html')


@preview_bp.get('/register')
def register():
    return render_template('auth/register.html')


@preview_bp.get('/menu')
def menu():
    return render_template('menu/index.html',
                           categories=cats, items=menu_items, cart_total=279,
                           current_user=FakeUser(), active_tab='menu')


@preview_bp.get('/order/create')
def order_create():
    return render_template('orders/create.html',
                           order_items=order_items, total_price=279,
                           current_user=FakeUser(), active_tab='orders')


@preview_bp.get('/order/select_table')
def order_select_table():
    selected = request.args.get('selected', type=int)

    statuses = dict(table_statuses)
    if selected:
        for tid in statuses:
            if statuses[tid] in ('selected', 'free'):
                statuses[tid] = 'selected' if tid == selected else 'free'

    if request.headers.get('HX-Request'):
        return render_template('orders/_tables_grid.html',
                               tables=tables, table_statuses=statuses, order=order)

    return render_template('orders/select_table.html',
                           order=order, tables=tables, table_statuses=statuses,
                           current_user=FakeUser(), active_tab='orders')


@preview_bp.get('/order/status')
def order_status():
    return render_template('orders/status.html',
                           order=order,
                           current_user=FakeUser(), active_tab='orders')


@preview_bp.get('/orders')
def my_orders():
    return render_template('orders/my_orders.html',
                           orders=admin_orders,
                           current_user=FakeUser(), active_tab='orders')


@preview_bp.get('/reservations')
def my_reservations():
    return render_template('reservations/index.html',
                           reservations=reservations,
                           current_user=FakeUser(), active_tab='reservations')


@preview_bp.get('/admin/orders')
def admin_orders_page():
    counts = {'all': 5, 'pending': 2, 'confirmed': 2, 'ready': 1}
    return render_template('admin/index.html',
                           orders=admin_orders, counts=counts,
                           active_count=5, today=now.strftime('%d.%m.%Y'),
                           current_user=FakeAdmin(), active_tab='orders')


@preview_bp.get('/admin/menu')
def admin_menu_page():
    counts = {'all': 5, 'available': 4, 'unavailable': 1}
    return render_template('admin/menu.html',
                           items=menu_items, counts=counts,
                           current_user=FakeAdmin(), active_tab='menu')
