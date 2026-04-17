from flask import Blueprint, render_template, redirect, url_for, flash, request, session, abort
from flask_login import login_required, current_user
from datetime import datetime
from app import db
from app.models import Order, OrderItem, MenuItem, Reservation

orders_bp = Blueprint('orders', __name__)

@orders_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    cart = session.get('cart', {})
    if request.method == 'GET':
        if not cart:
            flash('Корзина пуста')
            return redirect(url_for('menu.index'))
        
        # Загружаем блюда из базы для актуальных цен [3]
        items = MenuItem.query.filter(MenuItem.id.in_([int(k) for k in cart.keys()])).all()
        positions = [{'item': item, 'quantity': cart[str(item.id)], 'subtotal': item.price * cart[str(item.id)]} for item in items]
        cart_total = sum(pos['subtotal'] for pos in positions)
        
        return render_template('orders/create.html', positions=positions, cart_total=cart_total) [3, 4]

    # Обработка POST запроса
    if Order.get_active_count(current_user.id) >= 3:
        flash('У вас уже 3 активных заказа')
        return redirect(url_for('orders.create')) [4]
        
    pickup_time = request.form.get('pickup_time')
    comment = request.form.get('comment', '')
    reserve = request.form.get('reserve')
    pickup_dt = datetime.strptime(pickup_time, '%Y-%m-%dT%H:%M') [4]
    
    order = Order(user_id=current_user.id, pickup_time=pickup_dt, comment=comment, status='pending')
    db.session.add(order)
    db.session.flush() # Получаем order.id до коммита [2]
    
    for item_id, qty in cart.items():
        oi = OrderItem(order_id=order.id, menu_item_id=int(item_id), quantity=qty)
        db.session.add(oi) [2]
        
    order.calculate_total()
    db.session.commit()
    session.pop('cart', None) [2, 5]
    
    if reserve:
        return redirect(url_for('reservations.select_table', order_id=order.id)) [5]
    return redirect(url_for('orders.status', id=order.id)) [5]

@orders_bp.route('/<int:id>/status', methods=['GET'])
@login_required
def status(id):
    order = Order.query.get_or_404(id)
    if order.user_id != current_user.id:
        abort(403) [5]
    reservation = order.reservation
    return render_template('orders/status.html', order=order, reservation=reservation) [6]

@orders_bp.route('/<int:id>/badge', methods=['GET'])
@login_required
def badge(id):
    order = Order.query.get_or_404(id)
    if order.user_id != current_user.id:
        abort(403)
    return render_template('orders/_status_badge.html', order=order) [6]

@orders_bp.route('/<int:id>/cancel', methods=['POST'])
@login_required
def cancel(id):
    order = Order.query.get_or_404(id)
    if order.user_id != current_user.id:
        abort(403)
    if not order.is_cancellable():
        flash('Этот заказ уже нельзя отменить')
        return redirect(url_for('orders.status', id=id)) [7]
        
    order.status = 'cancelled'
    if order.reservation:
        order.reservation.status = 'cancelled' [7]
    db.session.commit()
    flash('Заказ отменён.')
    return redirect(url_for('orders.status', id=id)) [8]

@orders_bp.route('/<int:id>/pay', methods=['POST'])
@login_required
def pay(id):
    order = Order.query.get_or_404(id)
    if order.user_id != current_user.id:
        abort(403)
    order.status = 'paid'
    db.session.commit()
    flash('Оплата прошла успешно!')
    return redirect(url_for('orders.status', id=id)) [8]