from flask import Blueprint, render_template, redirect, url_for, flash, request, session, abort
from flask_login import login_required, current_user
from app.extensions import db, limiter
from app.models import Order, OrderItem, MenuItem
from app.repositories import order_repository
from app.services import order_service, reservation_service, pubsub
from app.utils.timezones import parse_local_to_utc

orders_bp = Blueprint('orders', __name__)

def _my_orders_list(user_id):
    reservation_service.activate_started()
    reservation_service.complete_expired()
    order_service.expire_overdue()
    return Order.query.filter_by(user_id=user_id).order_by(Order.created_at.desc()).all()


@orders_bp.route('/', methods=['GET'])
@login_required
def my_orders():
    orders = _my_orders_list(current_user.id)
    return render_template('orders/my_orders.html', orders=orders)


@orders_bp.route('/list', methods=['GET'])
@login_required
def my_orders_list():
    """Партиал списка заказов для HTMX-рефетча по SSE."""
    orders = _my_orders_list(current_user.id)
    return render_template('orders/_my_orders_list.html', orders=orders)

@orders_bp.route('/create', methods=['GET', 'POST'])
@login_required
@limiter.limit('30 per minute', methods=['POST'])
def create():
    cart = session.get('cart', {})
    draft = session.get('order_draft')

    if request.method == 'GET':
        if not cart:
            flash('Корзина пуста', 'danger')
            return redirect(url_for('menu.index'))

        items = MenuItem.query.filter(MenuItem.id.in_([int(k) for k in cart.keys()])).all()
        order_items = [
            type('CartLine', (), {'menu_item': item, 'quantity': cart[str(item.id)]})()
            for item in items
        ]
        total_price = sum(item.price * cart[str(item.id)] for item in items)

        return render_template(
            'orders/create.html',
            order_items=order_items,
            total_price=total_price,
            draft=draft,
        )

    # POST
    if not cart:
        flash('Корзина пуста', 'danger')
        return redirect(url_for('menu.index'))

    if order_repository.get_active_count(current_user.id) >= 3:
        flash('У вас уже 3 активных заказа', 'danger')
        return redirect(url_for('orders.create'))

    pickup_time = request.form.get('pickup_time')
    comment = request.form.get('comment', '')
    reserve = request.form.get('reserve') or request.form.get('reserve_table')

    try:
        pickup_dt = parse_local_to_utc(pickup_time)
    except (TypeError, ValueError):
        flash('Укажите корректное время получения', 'danger')
        return redirect(url_for('orders.create'))

    if reserve:
        # Заказ создаётся в reservations.select_table POST вместе с бронью; здесь только draft.
        session['order_draft'] = {
            'cart': dict(cart),
            'pickup_time': pickup_time,
            'comment': comment,
        }
        return redirect(url_for('reservations.select_table'))

    order = Order(user_id=current_user.id, pickup_time=pickup_dt, comment=comment, status='pending')
    db.session.add(order)
    db.session.flush()

    for item_id, qty in cart.items():
        oi = OrderItem(order_id=order.id, menu_item_id=int(item_id), quantity=qty)
        db.session.add(oi)

    db.session.flush()
    order_service.calculate_total(order)
    db.session.commit()
    pubsub.publish({
        'type': 'order-new',
        'order_id': order.id,
        'user_id': current_user.id,
    })
    session.pop('cart', None)
    session.pop('order_draft', None)

    return redirect(url_for('orders.status', id=order.id))


@orders_bp.route('/<int:id>/status', methods=['GET'])
@login_required
def status(id):
    reservation_service.activate_started()
    reservation_service.complete_expired()
    order_service.expire_overdue()
    order = order_repository.get_by_id(id)
    if order is None:
        abort(404)
    if order.user_id != current_user.id:
        abort(403)
    reservation = order.reservation
    return render_template('orders/status.html', order=order, reservation=reservation)


@orders_bp.route('/<int:id>/status-block', methods=['GET'])
@login_required
def status_block(id):
    """Партиал шкалы статуса для HTMX-рефетча по SSE."""
    order = order_repository.get_by_id(id)
    if order is None:
        abort(404)
    if order.user_id != current_user.id:
        abort(403)
    return render_template('orders/_status_block.html', order=order)


@orders_bp.route('/<int:id>/badge', methods=['GET'])
@login_required
def badge(id):
    order = order_repository.get_by_id(id)
    if order is None:
        abort(404)
    if order.user_id != current_user.id:
        abort(403)
    return render_template('orders/_status_badge.html', order=order)


@orders_bp.route('/<int:id>/cancel', methods=['POST'])
@login_required
@limiter.limit('20 per minute')
def cancel(id):
    order = order_repository.get_by_id(id)
    if order is None:
        abort(404)
    if order.user_id != current_user.id:
        abort(403)
    if not order_service.can_cancel(order):
        flash('Этот заказ уже нельзя отменить', 'danger')
        return redirect(url_for('orders.status', id=id))

    order.status = 'cancelled'
    if order.reservation:
        order.reservation.status = 'cancelled'
    db.session.commit()
    flash('Заказ отменён.', 'success')
    return redirect(url_for('orders.status', id=id))


@orders_bp.route('/<int:id>/pay', methods=['POST'])
@login_required
def pay(id):
    order = order_repository.get_by_id(id)
    if order is None:
        abort(404)
    if order.user_id != current_user.id:
        abort(403)
    if order.is_paid:
        flash('Заказ уже оплачен', 'info')
        return redirect(url_for('orders.status', id=id))
    if order.status not in ('pending', 'confirmed', 'ready'):
        flash('Заказ нельзя оплатить онлайн в текущем статусе', 'danger')
        return redirect(url_for('orders.status', id=id))
    order.is_paid = True
    db.session.commit()
    flash('Оплата прошла успешно!', 'success')
    return redirect(url_for('orders.status', id=id))
