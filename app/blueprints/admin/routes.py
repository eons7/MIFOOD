from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app import db
from app.models import Order, OrderItem, MenuItem, Category, Table, Reservation
import uuid
import os

admin_bp = Blueprint('admin', __name__)

# Вынесем проверку в функцию-хелпер для удобства
def check_admin():
    if not current_user.is_admin:
        abort(403) [14]

@admin_bp.route('/orders', methods=['GET'])
@login_required
def orders():
    check_admin()
    status_filter = request.args.get('status')
    query = Order.query.order_by(Order.pickup_time.asc())
    if status_filter:
        query = query.filter_by(status=status_filter)
    else:
        query = query.filter(Order.status.in_(['pending','confirmed','ready'])) [14]
    return render_template('admin/orders.html', orders=query.all(), status_filter=status_filter) [15]

@admin_bp.route('/orders/<int:id>/status', methods=['POST'])
@login_required
def update_order_status(id):
    check_admin()
    new_status = request.form.get('status')
    order = Order.query.get_or_404(id)
    allowed = {
        'pending':   ['confirmed', 'cancelled'],
        'confirmed': ['ready', 'cancelled'],
        'ready':     ['completed', 'cancelled'],
    } [15]
    if new_status not in allowed.get(order.status, []):
        abort(400) [16]
        
    order.status = new_status
    db.session.commit()
    return redirect(url_for('admin.orders')) [16]

@admin_bp.route('/menu', methods=['GET'])
@login_required
def menu_list():
    check_admin()
    availability = request.args.get('availability')
    category_id = request.args.get('category_id')
    query = MenuItem.query
    if availability == 'active':
        query = query.filter_by(is_available=True)
    elif availability == 'hidden':
        query = query.filter_by(is_available=False) [16]
    if category_id:
        query = query.filter_by(category_id=category_id)
        
    items = query.order_by(MenuItem.name).all()
    categories = Category.query.all()
    return render_template('admin/menu.html', items=items, categories=categories) [17]

@admin_bp.route('/menu/add', methods=['GET', 'POST'])
@login_required
def add_item():
    check_admin()
    if request.method == 'GET':
        return render_template('admin/menu_add.html', categories=Category.query.all()) [17]
        
    name = request.form.get('name')
    description = request.form.get('description')
    price = request.form.get('price')
    category_id = request.form.get('category_id')
    
    if not name or not price:
        flash('Имя и цена обязательны')
        return redirect(url_for('admin.add_item')) [17]
        
    image_url = None
    file = request.files.get('photo')
    if file:
        filename = str(uuid.uuid4()) + os.path.splitext(file.filename)[18]
        file.save(os.path.join('app', 'static', 'uploads', filename))
        image_url = '/static/uploads/' + filename [19]
        
    item = MenuItem(name=name, description=description, price=float(price), category_id=int(category_id), image_url=image_url, is_available=True)
    db.session.add(item)
    db.session.commit()
    flash('Блюдо добавлено.')
    return redirect(url_for('admin.menu_list')) [19]

@admin_bp.route('/menu/<int:id>/toggle', methods=['POST'])
@login_required
def toggle_item(id):
    check_admin()
    item = MenuItem.query.get_or_404(id)
    item.toggle_availability() [20]
    db.session.commit()
    flash('Блюдо возвращено в меню' if item.is_available else 'Блюдо скрыто')
    return redirect(url_for('admin.menu_list')) [20]

@admin_bp.route('/menu/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_item(id):
    check_admin()
    item = MenuItem.query.get_or_404(id)
    if request.method == 'GET':
        return render_template('admin/menu_edit.html', item=item, categories=Category.query.all()) [20]
        
    item.name = request.form.get('name')
    item.description = request.form.get('description')
    item.price = float(request.form.get('price'))
    item.category_id = int(request.form.get('category_id')) [21]
    
    file = request.files.get('photo')
    if file:
        filename = str(uuid.uuid4()) + os.path.splitext(file.filename)[18]
        file.save(os.path.join('app', 'static', 'uploads', filename))
        item.image_url = '/static/uploads/' + filename [21]
        
    db.session.commit()
    flash('Изменения сохранены.')
    return redirect(url_for('admin.menu_list')) [21]

@admin_bp.route('/tables', methods=['GET'])
@login_required
def tables():
    check_admin()
    return render_template('admin/tables.html', tables=Table.query.order_by(Table.number).all()) [21]

@admin_bp.route('/tables/add', methods=['POST'])
@login_required
def add_table():
    check_admin()
    number = request.form.get('number', type=int)
    seats = request.form.get('seats', type=int)
    if Table.query.filter_by(number=number).first():
        flash('Стол с таким номером уже существует')
        return redirect(url_for('admin.tables')) [22]
        
    table = Table(number=number, seats=seats, is_active=True)
    db.session.add(table)
    db.session.commit()
    flash('Стол добавлен.')
    return redirect(url_for('admin.tables')) [22]

@admin_bp.route('/tables/<int:id>/toggle', methods=['POST'])
@login_required
def toggle_table(id):
    check_admin()
    table = Table.query.get_or_404(id)
    table.is_active = not table.is_active
    db.session.commit()
    flash('Стол активирован' if table.is_active else 'Стол закрыт')
    return redirect(url_for('admin.tables')) [23]