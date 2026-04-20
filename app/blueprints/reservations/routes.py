from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from datetime import timedelta

from app.extensions import db
from app.models import Table
from app.repositories import order_repository, reservation_repository
from app.services import reservation_service

reservations_bp = Blueprint('reservations', __name__)


@reservations_bp.route('/select-table', methods=['GET', 'POST'])
@login_required
def select_table():
    if request.method == 'GET':
        order_id = request.args.get('order_id', type=int)
        if not order_id:
            abort(400)
        order = order_repository.get_by_id(order_id)
        if order is None:
            abort(404)
        if order.user_id != current_user.id:
            abort(403)

        tables = Table.query.filter_by(is_active=True).all()
        free_tables, busy_tables = [], []
        end = order.pickup_time + timedelta(hours=1)
        for table in tables:
            if reservation_repository.has_conflict(table.id, order.pickup_time, end):
                busy_tables.append(table)
            else:
                free_tables.append(table)

        return render_template(
            'reservations/select_table.html',
            order=order, free_tables=free_tables, busy_tables=busy_tables,
        )

    # POST
    order_id = request.form.get('order_id', type=int)
    table_id = request.form.get('table_id', type=int)
    duration = request.form.get('duration', type=int)

    order = order_repository.get_by_id(order_id)
    if order is None:
        abort(404)
    if order.user_id != current_user.id:
        abort(403)

    end_time = order.pickup_time + timedelta(minutes=duration)
    if reservation_repository.has_conflict(table_id, order.pickup_time, end_time):
        flash('Стол уже занят, выберите другой', 'danger')
        return redirect(url_for('reservations.select_table', order_id=order_id))

    reservation_service.create(
        user_id=current_user.id,
        table_id=table_id,
        order_id=order_id,
        start_time=order.pickup_time,
        end_time=end_time,
    )
    flash('Стол забронирован!', 'success')
    return redirect(url_for('orders.status', id=order_id))


@reservations_bp.route('/', methods=['GET'])
@login_required
def index():
    reservations = reservation_repository.get_by_user(current_user.id)
    active = [r for r in reservations if r.status == 'active']
    history = [r for r in reservations if r.status != 'active']
    return render_template('reservations/index.html', active=active, history=history)


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
