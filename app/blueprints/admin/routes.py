import os
import uuid

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.models import MenuItem, Category, Order, Table
from app.repositories import menu_repository, order_repository
from app.services import menu_service

admin_bp = Blueprint('admin', __name__)

# FSM переходов: из какого статуса в какой можно перейти
ORDER_TRANSITIONS = {
    'pending':   ['confirmed', 'paid', 'cancelled'],
    'paid':      ['confirmed', 'cancelled'],
    'confirmed': ['ready', 'cancelled'],
    'ready':     ['completed'],
    'completed': [],
    'cancelled': [],
}


def check_admin():
    if not current_user.is_admin:
        abort(403)


@admin_bp.route('/orders', methods=['GET'])
@login_required
def orders():
    check_admin()
    status_filter = request.args.get('status')
    query = Order.query.order_by(Order.pickup_time.asc())
    if status_filter:
        query = query.filter_by(status=status_filter)
    else:
        query = query.filter(Order.status.in_(['pending', 'confirmed', 'ready', 'paid']))
    return render_template('admin/orders.html', orders=query.all(), status_filter=status_filter, transitions=ORDER_TRANSITIONS)


@admin_bp.route('/orders/<int:id>/status', methods=['POST'])
@login_required
def update_order_status(id):
    check_admin()
    new_status = request.form.get('status')
    order = order_repository.get_by_id(id)
    if order is None:
        abort(404)
    if new_status not in ORDER_TRANSITIONS.get(order.status, []):
        flash('Недопустимый переход статуса', 'danger')
        return redirect(url_for('admin.orders'))

    order.status = new_status
    db.session.commit()
    return redirect(url_for('admin.orders'))


@admin_bp.route('/menu', methods=['GET'])
@login_required
def menu_list():
    check_admin()
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
@login_required
def add_item():
    check_admin()
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
@login_required
def toggle_item(id):
    check_admin()
    item = menu_repository.get_item_by_id(id)
    if item is None:
        abort(404)
    menu_service.toggle_availability(item)
    flash('Блюдо возвращено в меню' if item.is_available else 'Блюдо скрыто', 'info')
    return redirect(url_for('admin.menu_list'))


@admin_bp.route('/menu/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_item(id):
    check_admin()
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
@login_required
def tables():
    check_admin()
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
@login_required
def toggle_table(id):
    check_admin()
    table = Table.query.get(id)
    if table is None:
        abort(404)
    table.is_active = not table.is_active
    db.session.commit()
    flash(
        f'Стол №{table.number} {"активирован" if table.is_active else "скрыт"}',
        'info',
    )
    return redirect(url_for('admin.tables'))
