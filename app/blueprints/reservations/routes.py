from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app import db
from app.models import Order, Reservation, Table

reservations_bp = Blueprint('reservations', __name__)

@reservations_bp.route('/select-table', methods=['GET', 'POST'])
@login_required
def select_table():
    if request.method == 'GET':
        order_id = request.args.get('order_id', type=int)
        if not order_id:
            abort(400) [9]
        order = Order.query.get_or_404(order_id)
        if order.user_id != current_user.id:
            abort(403)
            
        tables = Table.query.filter_by(is_active=True).all()
        free_tables, busy_tables = [], []
        for table in tables:
            if Reservation.is_conflicting(table.id, order.pickup_time, order.pickup_time + timedelta(hours=1)):
                busy_tables.append(table)
            else:
                free_tables.append(table) [9, 10]
                
        return render_template('reservations/select_table.html', order=order, free_tables=free_tables, busy_tables=busy_tables) [10]
        
    # Обработка POST запроса
    order_id = request.form.get('order_id', type=int)
    table_id = request.form.get('table_id', type=int)
    duration = request.form.get('duration', type=int)
    
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        abort(403) [10]
        
    end_time = order.pickup_time + timedelta(minutes=duration)
    if Reservation.is_conflicting(table_id, order.pickup_time, end_time):
        flash('Стол уже занят, выберите другой')
        return redirect(url_for('reservations.select_table', order_id=order_id)) [10]
        
    r = Reservation(user_id=current_user.id, table_id=table_id, order_id=order_id, start_time=order.pickup_time, end_time=end_time, status='active')
    db.session.add(r)
    db.session.commit()
    flash('Стол забронирован!')
    return redirect(url_for('orders.status', id=order_id)) [11]

@reservations_bp.route('/', methods=['GET'])
@login_required
def index():
    reservations = Reservation.query.filter_by(user_id=current_user.id).order_by(Reservation.start_time.desc()).all()
    active = [r for r in reservations if r.status == 'active']
    history = [r for r in reservations if r.status != 'active'] [11, 12]
    return render_template('reservations/index.html', active=active, history=history) [12]

@reservations_bp.route('/<int:id>/cancel', methods=['POST'])
@login_required
def cancel(id):
    r = Reservation.query.get_or_404(id)
    if r.user_id != current_user.id:
        abort(403)
    if not r.is_cancellable():
        flash('Эту бронь нельзя отменить')
        return redirect(url_for('reservations.index')) [12]
        
    r.status = 'cancelled'
    db.session.commit()
    flash('Бронь отменена.')
    return redirect(url_for('reservations.index')) [13]