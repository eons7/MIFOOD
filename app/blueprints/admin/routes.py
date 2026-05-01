import os
import uuid
from datetime import timedelta

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from app.extensions import db
from app.models import MenuItem, Category, Order, Table
from app.repositories import menu_repository, order_repository
from app.services import menu_service, order_service, pubsub, reservation_service
from app.utils.security import admin_required, audit

admin_bp = Blueprint('admin', __name__)

# Кухонный FSM. Ось is_paid отдельная.
ORDER_TRANSITIONS = {
    'pending':   ['confirmed', 'cancelled'],
    'confirmed': ['ready', 'cancelled'],
    'ready':     ['completed'],
    'completed': [],
    'cancelled': [],
    'expired':   [],
}


def _orders_context(status_filter):
    """Контекст для шаблона списка заказов: orders + extend_info + status_labels."""
    reservation_service.activate_started()
    reservation_service.complete_expired()
    order_service.expire_overdue()

    query = Order.query.order_by(Order.pickup_time.asc())
    if status_filter:
        query = query.filter_by(status=status_filter)
    else:
        query = query.filter(Order.status.in_(['pending', 'confirmed', 'ready']))
    orders = query.all()

    extend_info = {}
    for o in orders:
        if order_service.can_extend(o):
            mins = order_service.max_extend_minutes(o)
            extend_info[o.id] = {
                'minutes': mins,
                'until': (o.pickup_time + timedelta(minutes=mins)).strftime('%H:%M'),
            }
    return {
        'orders': orders,
        'status_filter': status_filter,
        'transitions': ORDER_TRANSITIONS,
        'extend_info': extend_info,
        'status_labels': {
            'pending': 'Ожидает', 'confirmed': 'Принят', 'ready': 'Готов',
            'completed': 'Выдан', 'cancelled': 'Отменён', 'expired': 'Не забран',
        },
    }


@admin_bp.route('/orders', methods=['GET'])
@admin_required
def orders():
    ctx = _orders_context(request.args.get('status'))
    return render_template('admin/orders.html', **ctx)


@admin_bp.route('/orders/board', methods=['GET'])
@admin_required
def orders_board():
    """Партиал доски заказов для HTMX-рефетча по SSE."""
    ctx = _orders_context(request.args.get('status'))
    return render_template('admin/_orders_board.html', **ctx)


@admin_bp.route('/orders/<int:id>/status', methods=['POST'])
@admin_required
def update_order_status(id):
    new_status = request.form.get('status')
    order = order_repository.get_by_id(id)
    if order is None:
        abort(404)
    if new_status not in ORDER_TRANSITIONS.get(order.status, []):
        flash('Недопустимый переход статуса', 'danger')
        return redirect(url_for('admin.orders'))

    old_status = order.status
    order.status = new_status
    if new_status == 'completed':
        order.is_paid = True
    db.session.commit()
    audit('order.status_change', order_id=order.id, old=old_status, new=new_status)
    pubsub.publish({
        'type': 'order-status',
        'order_id': order.id,
        'status': new_status,
        'user_id': order.user_id,
    })
    return redirect(url_for('admin.orders'))


@admin_bp.route('/orders/<int:id>/extend', methods=['POST'])
@admin_required
def extend_order(id):
    order = order_repository.get_by_id(id)
    if order is None:
        abort(404)
    if not order_service.can_extend(order):
        flash('Нельзя продлить: нет брони или следующая бронь слишком близко.', 'danger')
        return redirect(url_for('admin.orders'))

    minutes = order_service.extend(order)
    if minutes == 0:
        flash('Не удалось продлить — следующая бронь начинается слишком скоро.', 'danger')
    else:
        flash(f'Продлено на {minutes} мин (до {order.pickup_time.strftime("%H:%M")}).', 'success')
        audit('order.extend', order_id=order.id, minutes=minutes)
        pubsub.publish({
            'type': 'order-status',
            'order_id': order.id,
            'status': order.status,
            'user_id': order.user_id,
        })
    return redirect(url_for('admin.orders'))


@admin_bp.route('/menu', methods=['GET'])
@admin_required
def menu_list():
    availability = request.args.get('availability')
    category_id = request.args.get('category_id', type=int)
    query = MenuItem.query
    if availability == 'active':
        query = query.filter_by(is_available=True)
    elif availability == 'hidden':
        query = query.filter_by(is_available=False)
    if category_id:
        query = query.filter_by(category_id=category_id)

    items = query.order_by(MenuItem.name).all()
    categories = Category.query.order_by(Category.name).all()
    counts = {
        'all':          MenuItem.query.count(),
        'available':    MenuItem.query.filter_by(is_available=True).count(),
        'unavailable':  MenuItem.query.filter_by(is_available=False).count(),
    }
    return render_template('admin/menu.html', items=items, categories=categories, counts=counts)


@admin_bp.route('/menu/add', methods=['GET', 'POST'])
@admin_required
def add_item():
    if request.method == 'GET':
        return render_template('admin/menu_add.html', categories=Category.query.order_by(Category.name).all())

    name = request.form.get('name')
    description = request.form.get('description')
    price = request.form.get('price')
    category_id = request.form.get('category_id')

    if not name or not price:
        flash('Имя и цена обязательны', 'danger')
        return redirect(url_for('admin.add_item'))

    image_url = None
    file = request.files.get('photo')
    if file and file.filename:
        filename = str(uuid.uuid4()) + os.path.splitext(file.filename)[1]
        file.save(os.path.join('app', 'static', 'uploads', filename))
        image_url = '/static/uploads/' + filename

    item = MenuItem(
        name=name, description=description, price=float(price),
        category_id=int(category_id), image_url=image_url, is_available=True,
    )
    menu_repository.save_item(item)
    flash('Блюдо добавлено.', 'success')
    return redirect(url_for('admin.menu_list'))


@admin_bp.route('/menu/<int:id>/toggle', methods=['POST'])
@admin_required
def toggle_item(id):
    item = menu_repository.get_item_by_id(id)
    if item is None:
        abort(404)
    menu_service.toggle_availability(item)
    audit('menu.toggle', item_id=item.id, available=item.is_available)
    flash('Блюдо возвращено в меню' if item.is_available else 'Блюдо скрыто', 'info')
    return redirect(url_for('admin.menu_list'))


@admin_bp.route('/menu/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_item(id):
    item = menu_repository.get_item_by_id(id)
    if item is None:
        abort(404)
    if request.method == 'GET':
        return render_template('admin/menu_edit.html', item=item, categories=Category.query.order_by(Category.name).all())

    item.name = request.form.get('name')
    item.description = request.form.get('description')
    item.price = float(request.form.get('price'))
    item.category_id = int(request.form.get('category_id'))

    file = request.files.get('photo')
    if file and file.filename:
        filename = str(uuid.uuid4()) + os.path.splitext(file.filename)[1]
        file.save(os.path.join('app', 'static', 'uploads', filename))
        item.image_url = '/static/uploads/' + filename

    menu_repository.save_item(item)
    flash('Изменения сохранены.', 'success')
    return redirect(url_for('admin.menu_list'))


@admin_bp.route('/tables', methods=['GET', 'POST'])
@admin_required
def tables():
    if request.method == 'POST':
        number = request.form.get('number', type=int)
        seats = request.form.get('seats', type=int)
        if not number or not seats or number < 1 or seats < 1:
            flash('Укажите номер и количество мест', 'danger')
            return redirect(url_for('admin.tables'))
        if Table.query.filter_by(number=number).first():
            flash(f'Стол №{number} уже существует', 'danger')
            return redirect(url_for('admin.tables'))
        db.session.add(Table(number=number, seats=seats, is_active=True))
        db.session.commit()
        flash(f'Стол №{number} добавлен', 'success')
        return redirect(url_for('admin.tables'))

    all_tables = Table.query.order_by(Table.number).all()
    return render_template('admin/tables.html', tables=all_tables)


@admin_bp.route('/tables/<int:id>/toggle', methods=['POST'])
@admin_required
def toggle_table(id):
    table = Table.query.get(id)
    if table is None:
        abort(404)
    table.is_active = not table.is_active
    db.session.commit()
    audit('table.toggle', table_id=table.id, active=table.is_active)
    flash(
        f'Стол №{table.number} {"активирован" if table.is_active else "скрыт"}',
        'info',
    )
    return redirect(url_for('admin.tables'))
