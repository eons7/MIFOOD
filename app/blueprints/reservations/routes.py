from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, session
from flask_login import login_required, current_user
from datetime import timedelta

from app.extensions import db
from app.models import Table
from app.models.order import Order, OrderItem
from app.models.menu import MenuItem
from app.repositories import order_repository, reservation_repository
from app.services import order_service, reservation_service, pubsub
from app.utils.timezones import parse_local_to_utc

reservations_bp = Blueprint('reservations', __name__)

# Допустимые длительности брони (минуты). Должно совпадать со списком в шаблоне.
ALLOWED_DURATIONS = (5, 10, 15, 20, 25, 30, 35, 40, 45)
DEFAULT_DURATION = 45


def _tables_for_duration(pickup_dt, duration: int):
    """Делит активные столы на свободные/занятые с учётом конкретной длительности.
    Используется и при первом GET, и при HTMX-перерисовке после смены duration.
    """
    end = pickup_dt + timedelta(minutes=duration)
    tables = Table.query.filter_by(is_active=True).order_by(Table.number).all()
    free, busy = [], []
    for table in tables:
        if reservation_repository.has_conflict(table.id, pickup_dt, end):
            busy.append(table)
        else:
            free.append(table)
    return free, busy


@reservations_bp.route('/select-table', methods=['GET', 'POST'])
@login_required
def select_table():
    """Шаг 2 оформления заказа с бронью. Заказ ещё НЕ создан в БД —
    данные лежат в session['order_draft']. Здесь и финализируем."""
    draft = session.get('order_draft')
    if not draft:
        flash('Сначала оформите заказ', 'warning')
        return redirect(url_for('orders.create'))

    try:
        pickup_dt = parse_local_to_utc(draft['pickup_time'])
    except (KeyError, TypeError, ValueError):
        session.pop('order_draft', None)
        flash('Черновик заказа повреждён. Попробуйте ещё раз.', 'danger')
        return redirect(url_for('orders.create'))

    if request.method == 'GET':
        # Освобождаем столы, у которых бронь уже истекла
        reservation_service.activate_started()
        reservation_service.complete_expired()

        # Собираем «лёгкий» вьюхи объект с теми полями, что ждёт шаблон
        cart = draft.get('cart', {})
        items = MenuItem.query.filter(MenuItem.id.in_([int(k) for k in cart.keys()])).all()
        total_price = sum(item.price * cart[str(item.id)] for item in items)

        free_tables, busy_tables = _tables_for_duration(pickup_dt, DEFAULT_DURATION)

        return render_template(
            'reservations/select_table.html',
            pickup_time=pickup_dt,
            total_price=total_price,
            free_tables=free_tables,
            busy_tables=busy_tables,
            duration=DEFAULT_DURATION,
            durations=ALLOWED_DURATIONS,
        )

    # POST: финализируем — создаём Order + OrderItems + (опционально) Reservation атомарно.
    if order_repository.get_active_count(current_user.id) >= 3:
        flash('У вас уже 3 активных заказа', 'danger')
        return redirect(url_for('reservations.select_table'))

    cart = draft.get('cart', {})
    if not cart:
        session.pop('order_draft', None)
        flash('Корзина пуста', 'danger')
        return redirect(url_for('menu.index'))

    action = request.form.get('action', 'confirm')
    table_id = request.form.get('table_id', type=int)
    duration = request.form.get('duration', type=int) or DEFAULT_DURATION
    if duration not in ALLOWED_DURATIONS:
        duration = DEFAULT_DURATION

    # Заранее проверяем конфликт по столу — чтобы не создавать заказ зря, если стол только что заняли.
    if action == 'confirm':
        if not table_id:
            flash('Выберите стол или нажмите «Пропустить бронирование»', 'danger')
            return redirect(url_for('reservations.select_table'))
        end_time = pickup_dt + timedelta(minutes=duration)
        if reservation_repository.has_conflict(table_id, pickup_dt, end_time):
            flash('Стол уже занят, выберите другой', 'danger')
            return redirect(url_for('reservations.select_table'))

    # Создаём заказ
    order = Order(
        user_id=current_user.id,
        pickup_time=pickup_dt,
        comment=draft.get('comment', ''),
        status='pending',
    )
    db.session.add(order)
    db.session.flush()
    for item_id, qty in cart.items():
        db.session.add(OrderItem(order_id=order.id, menu_item_id=int(item_id), quantity=qty))
    db.session.flush()
    order_service.calculate_total(order)

    if action == 'confirm':
        end_time = pickup_dt + timedelta(minutes=duration)
        reservation_service.create(
            user_id=current_user.id,
            table_id=table_id,
            order_id=order.id,
            start_time=pickup_dt,
            end_time=end_time,
        )
        # reservation_service.create сам делает commit, но Order уже flushed —
        # на тот же commit уйдёт.
        flash('Стол забронирован!', 'success')
    else:
        db.session.commit()
        flash('Заказ оформлен без брони', 'info')

    pubsub.publish({
        'type': 'order-new',
        'order_id': order.id,
        'user_id': current_user.id,
    })
    session.pop('cart', None)
    session.pop('order_draft', None)
    return redirect(url_for('orders.status', id=order.id))


def _user_reservations(user_id):
    reservation_service.activate_started()
    reservation_service.complete_expired()
    return reservation_repository.get_by_user(user_id)


@reservations_bp.route('/tables-list', methods=['GET'])
@login_required
def tables_list():
    """Партиал списка столов — HTMX-рефетч при смене длительности на странице
    выбора стола. Берёт pickup_time из текущего черновика заказа в session.
    """
    draft = session.get('order_draft')
    if not draft:
        abort(400)
    try:
        pickup_dt = parse_local_to_utc(draft['pickup_time'])
    except (KeyError, TypeError, ValueError):
        abort(400)

    duration = request.args.get('duration', type=int) or DEFAULT_DURATION
    if duration not in ALLOWED_DURATIONS:
        duration = DEFAULT_DURATION

    reservation_service.activate_started()
    reservation_service.complete_expired()
    free_tables, busy_tables = _tables_for_duration(pickup_dt, duration)
    return render_template(
        'reservations/_tables_list.html',
        free_tables=free_tables,
        busy_tables=busy_tables,
    )


@reservations_bp.route('/', methods=['GET'])
@login_required
def index():
    reservations = _user_reservations(current_user.id)
    return render_template('reservations/index.html', reservations=reservations)


@reservations_bp.route('/list', methods=['GET'])
@login_required
def list_partial():
    """Партиал списка броней — для HTMX-рефетча по SSE."""
    reservations = _user_reservations(current_user.id)
    return render_template('reservations/_list.html', reservations=reservations)


@reservations_bp.route('/<int:id>/cancel', methods=['POST'])
@login_required
def cancel(id):
    r = reservation_repository.get_by_id(id)
    if r is None:
        abort(404)
    if r.user_id != current_user.id:
        abort(403)
    if not reservation_service.can_cancel(r):
        flash('Эту бронь нельзя отменить', 'danger')
        return redirect(url_for('reservations.index'))

    reservation_service.cancel(r)
    flash('Бронь отменена.', 'success')
    return redirect(url_for('reservations.index'))
