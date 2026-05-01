"""Сценарии для order_service.expire_overdue / extend / max_extend_minutes
и reservation_repository.next_after.

Используем in-memory SQLite, чтобы не трогать dev-базу.
"""
import os
import pytest
from datetime import timedelta

os.environ['FLASK_ENV'] = 'testing'

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import User, Table, MenuItem, Category, Order, OrderItem  # noqa: E402
from app.models.reservation import Reservation  # noqa: E402
from app.repositories import reservation_repository  # noqa: E402
from app.services import order_service  # noqa: E402
from app.utils.timezones import now_utc_naive  # noqa: E402


@pytest.fixture
def app():
    app = create_app('testing')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def fixtures(app):
    """Базовые объекты: пользователь, стол, блюдо."""
    u = User(name='Test', email='t@t.t', password_hash='x')
    cat = Category(name='Cat')
    db.session.add_all([u, cat])
    db.session.flush()
    item = MenuItem(name='Pizza', price=100.0, category_id=cat.id, is_available=True)
    table = Table(number=1, seats=2, is_active=True)
    db.session.add_all([item, table])
    db.session.commit()
    return {'user': u, 'item': item, 'table': table}


def make_order(fixtures, status, pickup_offset_min, with_reservation=True,
                res_status='scheduled', res_offset_min=0, res_duration_min=60):
    """Создаёт заказ с опциональной бронью.
    pickup_offset_min — относительно now (отрицательно = в прошлом).
    res_offset_min — старт брони относительно now.
    """
    now = now_utc_naive()
    order = Order(
        user_id=fixtures['user'].id,
        pickup_time=now + timedelta(minutes=pickup_offset_min),
        status=status,
        total_price=100.0,
    )
    db.session.add(order)
    db.session.flush()
    db.session.add(OrderItem(order_id=order.id, menu_item_id=fixtures['item'].id, quantity=1))

    if with_reservation:
        start = now + timedelta(minutes=res_offset_min)
        r = Reservation(
            user_id=fixtures['user'].id,
            table_id=fixtures['table'].id,
            order_id=order.id,
            start_time=start,
            end_time=start + timedelta(minutes=res_duration_min),
            status=res_status,
        )
        db.session.add(r)
    db.session.commit()
    return order


# --------- expire_overdue ---------

def test_expire_ready_overdue_with_reservation(fixtures):
    """ready + pickup_time старше 15 мин → expired, бронь отменяется."""
    o = make_order(fixtures, 'ready', pickup_offset_min=-20,
                    res_status='active', res_offset_min=-30, res_duration_min=60)
    n = order_service.expire_overdue()
    db.session.refresh(o)
    db.session.refresh(o.reservation)
    assert n == 1
    assert o.status == 'expired'
    assert o.reservation.status == 'cancelled'


def test_expire_ready_within_threshold_not_expired(fixtures):
    """ready + pickup_time всего 10 мин назад → не expired."""
    o = make_order(fixtures, 'ready', pickup_offset_min=-10)
    n = order_service.expire_overdue()
    db.session.refresh(o)
    assert n == 0
    assert o.status == 'ready'


def test_expire_only_ready_not_pending(fixtures):
    """pending или confirmed заказ не expired, даже если давно просрочен."""
    o = make_order(fixtures, 'confirmed', pickup_offset_min=-60)
    n = order_service.expire_overdue()
    db.session.refresh(o)
    assert n == 0
    assert o.status == 'confirmed'


def test_expire_ready_without_reservation(fixtures):
    """ready без брони → всё равно expired (но бронь не трогаем)."""
    o = make_order(fixtures, 'ready', pickup_offset_min=-20, with_reservation=False)
    n = order_service.expire_overdue()
    db.session.refresh(o)
    assert n == 1
    assert o.status == 'expired'
    assert o.reservation is None


# --------- max_extend_minutes ---------

def test_extend_max_no_next_reservation(fixtures):
    """Нет следующей брони → можно продлить на полные 15 мин."""
    o = make_order(fixtures, 'ready', pickup_offset_min=5,
                    res_status='active', res_offset_min=-5, res_duration_min=10)
    assert order_service.max_extend_minutes(o) == 15


def test_extend_capped_by_next_reservation(fixtures):
    """Следующая бронь через 7 мин после end_time → можно продлить только на 7."""
    now = now_utc_naive()
    o = make_order(fixtures, 'ready', pickup_offset_min=5,
                    res_status='active', res_offset_min=-5, res_duration_min=10)
    # Следующая бронь на тот же стол, начинается через 7 мин после конца текущей.
    next_start = o.reservation.end_time + timedelta(minutes=7)
    db.session.add(Reservation(
        user_id=fixtures['user'].id, table_id=fixtures['table'].id, order_id=o.id,
        start_time=next_start, end_time=next_start + timedelta(minutes=60),
        status='scheduled',
    ))
    db.session.commit()
    assert order_service.max_extend_minutes(o) == 7


def test_extend_blocked_when_next_too_close(fixtures):
    """Следующая бронь через 3 мин → max=3, can_extend=False (порог 5)."""
    o = make_order(fixtures, 'ready', pickup_offset_min=5,
                    res_status='active', res_offset_min=-5, res_duration_min=10)
    next_start = o.reservation.end_time + timedelta(minutes=3)
    db.session.add(Reservation(
        user_id=fixtures['user'].id, table_id=fixtures['table'].id, order_id=o.id,
        start_time=next_start, end_time=next_start + timedelta(minutes=60),
        status='scheduled',
    ))
    db.session.commit()
    assert order_service.max_extend_minutes(o) == 3
    assert order_service.can_extend(o) is False


def test_extend_blocked_when_next_back_to_back(fixtures):
    """Следующая бронь начинается ровно в момент end_time → max=0."""
    o = make_order(fixtures, 'ready', pickup_offset_min=5,
                    res_status='active', res_offset_min=-5, res_duration_min=10)
    next_start = o.reservation.end_time
    db.session.add(Reservation(
        user_id=fixtures['user'].id, table_id=fixtures['table'].id, order_id=o.id,
        start_time=next_start, end_time=next_start + timedelta(minutes=60),
        status='scheduled',
    ))
    db.session.commit()
    assert order_service.max_extend_minutes(o) == 0
    assert order_service.can_extend(o) is False


def test_extend_no_reservation_zero(fixtures):
    """Заказ без брони → max=0, can_extend=False."""
    o = make_order(fixtures, 'ready', pickup_offset_min=5, with_reservation=False)
    assert order_service.max_extend_minutes(o) == 0
    assert order_service.can_extend(o) is False


def test_extend_completed_order_blocked(fixtures):
    """Выданный заказ нельзя продлить."""
    o = make_order(fixtures, 'completed', pickup_offset_min=-30,
                    res_status='completed', res_offset_min=-60, res_duration_min=30)
    assert order_service.can_extend(o) is False


# --------- extend (mutation) ---------

def test_extend_moves_pickup_and_reservation(fixtures):
    """extend двигает pickup_time и reservation.end_time на max минут."""
    o = make_order(fixtures, 'ready', pickup_offset_min=5,
                    res_status='active', res_offset_min=-5, res_duration_min=10)
    pickup_before = o.pickup_time
    end_before = o.reservation.end_time
    minutes = order_service.extend(o)
    assert minutes == 15
    assert o.pickup_time == pickup_before + timedelta(minutes=15)
    assert o.reservation.end_time == end_before + timedelta(minutes=15)


def test_extend_capped_actually_caps(fixtures):
    """Если зазор 6 мин — extend двигает на 6, не 15. Серверный capping."""
    o = make_order(fixtures, 'ready', pickup_offset_min=5,
                    res_status='active', res_offset_min=-5, res_duration_min=10)
    next_start = o.reservation.end_time + timedelta(minutes=6)
    db.session.add(Reservation(
        user_id=fixtures['user'].id, table_id=fixtures['table'].id, order_id=o.id,
        start_time=next_start, end_time=next_start + timedelta(minutes=60),
        status='scheduled',
    ))
    db.session.commit()
    end_before = o.reservation.end_time
    minutes = order_service.extend(o)
    assert minutes == 6
    assert o.reservation.end_time == end_before + timedelta(minutes=6)


def test_extend_blocked_returns_zero(fixtures):
    """Если max < 5 — extend ничего не делает, возвращает 0."""
    o = make_order(fixtures, 'ready', pickup_offset_min=5,
                    res_status='active', res_offset_min=-5, res_duration_min=10)
    next_start = o.reservation.end_time + timedelta(minutes=2)
    db.session.add(Reservation(
        user_id=fixtures['user'].id, table_id=fixtures['table'].id, order_id=o.id,
        start_time=next_start, end_time=next_start + timedelta(minutes=60),
        status='scheduled',
    ))
    db.session.commit()
    pickup_before = o.pickup_time
    minutes = order_service.extend(o)
    assert minutes == 0
    assert o.pickup_time == pickup_before  # ничего не двинулось


# --------- next_after ---------

def test_next_after_excludes_self(fixtures):
    """Текущая бронь не должна находить саму себя."""
    o = make_order(fixtures, 'ready', pickup_offset_min=5,
                    res_status='active', res_offset_min=-5, res_duration_min=10)
    r = o.reservation
    nxt = reservation_repository.next_after(r.table_id, r.end_time, exclude_id=r.id)
    assert nxt is None


def test_next_after_ignores_cancelled(fixtures):
    """Отменённая бронь не должна блокировать продление."""
    o = make_order(fixtures, 'ready', pickup_offset_min=5,
                    res_status='active', res_offset_min=-5, res_duration_min=10)
    next_start = o.reservation.end_time + timedelta(minutes=3)
    db.session.add(Reservation(
        user_id=fixtures['user'].id, table_id=fixtures['table'].id, order_id=o.id,
        start_time=next_start, end_time=next_start + timedelta(minutes=60),
        status='cancelled',
    ))
    db.session.commit()
    # Следующая бронь cancelled → max=15 (как будто её нет).
    assert order_service.max_extend_minutes(o) == 15
