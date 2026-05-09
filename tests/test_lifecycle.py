"""Тесты жизненного цикла Order и Reservation:
- допустимые/запрещённые FSM-переходы
- автоматический expire ready-заказов
- активация/завершение броней по времени
- продление брони с capping по соседней брони
"""
import os
import pytest
from datetime import timedelta

os.environ['FLASK_ENV'] = 'testing'

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import User, Table, MenuItem, Category, Order  # noqa: E402
from app.models.reservation import Reservation  # noqa: E402
from app.repositories import reservation_repository  # noqa: E402
from app.services import order_service, reservation_service  # noqa: E402
from app.blueprints.admin.routes import ORDER_TRANSITIONS  # noqa: E402
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
def base(app):
    u = User(name='U', email='u@u.u', password_hash='x')
    cat = Category(name='C')
    db.session.add_all([u, cat])
    db.session.flush()
    item = MenuItem(name='X', price=100.0, category_id=cat.id, is_available=True)
    table = Table(number=1, seats=2, is_active=True)
    db.session.add_all([item, table])
    db.session.commit()
    return {'user': u, 'item': item, 'table': table}


def make_order(base, status='pending', pickup_offset_min=30):
    now = now_utc_naive()
    o = Order(
        user_id=base['user'].id,
        pickup_time=now + timedelta(minutes=pickup_offset_min),
        status=status,
        total_price=100.0,
    )
    db.session.add(o)
    db.session.commit()
    return o


def make_reservation(base, order, status='scheduled', start_offset_min=0, duration_min=60):
    now = now_utc_naive()
    r = Reservation(
        user_id=base['user'].id,
        table_id=base['table'].id,
        order_id=order.id,
        start_time=now + timedelta(minutes=start_offset_min),
        end_time=now + timedelta(minutes=start_offset_min + duration_min),
        status=status,
    )
    db.session.add(r)
    db.session.commit()
    return r


# ───────── ORDER_TRANSITIONS — конечный автомат ─────────

class TestOrderFSM:
    def test_pending_can_go_to_confirmed_or_cancelled(self):
        assert set(ORDER_TRANSITIONS['pending']) == {'confirmed', 'cancelled'}

    def test_confirmed_can_go_to_ready_or_cancelled(self):
        assert set(ORDER_TRANSITIONS['confirmed']) == {'ready', 'cancelled'}

    def test_ready_can_only_go_to_completed(self):
        assert ORDER_TRANSITIONS['ready'] == ['completed']

    def test_terminal_states_have_no_transitions(self):
        for s in ('completed', 'cancelled', 'expired'):
            assert ORDER_TRANSITIONS[s] == []

    def test_pending_cannot_skip_to_ready(self):
        assert 'ready' not in ORDER_TRANSITIONS['pending']

    def test_completed_cannot_be_uncompleted(self):
        # Из completed никуда нельзя — заказ закрыт навсегда
        assert ORDER_TRANSITIONS['completed'] == []


# ───────── expire_overdue ─────────

class TestExpireOverdue:
    def test_ready_order_past_threshold_expires(self, base):
        # Заказ ready, pickup_time был 20 минут назад → старше 15-мин окна
        o = make_order(base, status='ready', pickup_offset_min=-20)
        n = order_service.expire_overdue()
        assert n == 1
        db.session.refresh(o)
        assert o.status == 'expired'

    def test_ready_order_within_threshold_stays(self, base):
        # pickup был 5 минут назад — ещё в пределах 15 мин ожидания
        o = make_order(base, status='ready', pickup_offset_min=-5)
        n = order_service.expire_overdue()
        assert n == 0
        db.session.refresh(o)
        assert o.status == 'ready'

    def test_expire_cancels_attached_scheduled_reservation(self, base):
        o = make_order(base, status='ready', pickup_offset_min=-30)
        r = make_reservation(base, o, status='scheduled', start_offset_min=10)
        order_service.expire_overdue()
        db.session.refresh(r)
        assert r.status == 'cancelled'

    def test_pending_order_not_affected_by_expire(self, base):
        # expire_overdue работает только с ready
        o = make_order(base, status='pending', pickup_offset_min=-100)
        order_service.expire_overdue()
        db.session.refresh(o)
        assert o.status == 'pending'


# ───────── reservation_service.activate_started / complete_expired ─────────

class TestReservationFSM:
    def test_scheduled_in_window_activates(self, base):
        o = make_order(base, status='confirmed')
        # бронь идёт прямо сейчас (start_offset = -10, duration = 60 → закончится через 50м)
        r = make_reservation(base, o, status='scheduled',
                              start_offset_min=-10, duration_min=60)
        n = reservation_service.activate_started()
        assert n == 1
        db.session.refresh(r)
        assert r.status == 'active'

    def test_scheduled_in_future_not_activated(self, base):
        o = make_order(base, status='confirmed')
        r = make_reservation(base, o, status='scheduled',
                              start_offset_min=30, duration_min=60)
        reservation_service.activate_started()
        db.session.refresh(r)
        assert r.status == 'scheduled'

    def test_active_with_expired_end_completes(self, base):
        o = make_order(base, status='confirmed')
        r = make_reservation(base, o, status='active',
                              start_offset_min=-120, duration_min=60)
        n = reservation_service.complete_expired()
        assert n == 1
        db.session.refresh(r)
        assert r.status == 'completed'

    def test_can_cancel_only_scheduled(self, base):
        o = make_order(base, status='confirmed')
        r_sched = make_reservation(base, o, status='scheduled', start_offset_min=10)
        assert reservation_service.can_cancel(r_sched) is True

        o2 = make_order(base, status='confirmed')
        r_active = make_reservation(base, o2, status='active', start_offset_min=-10)
        assert reservation_service.can_cancel(r_active) is False


# ───────── order_service.extend / max_extend_minutes ─────────

class TestExtend:
    def test_can_extend_requires_reservation(self, base):
        o = make_order(base, status='confirmed', pickup_offset_min=10)
        # без брони
        assert order_service.can_extend(o) is False

    def test_can_extend_works_with_active_reservation_and_no_next(self, base):
        o = make_order(base, status='confirmed', pickup_offset_min=10)
        make_reservation(base, o, status='scheduled', start_offset_min=10, duration_min=60)
        assert order_service.can_extend(o) is True

    def test_max_extend_capped_by_next_reservation(self, base):
        # Наша бронь: 0..60 мин от now. Следующая: 70..130 мин (gap = 10).
        o1 = make_order(base, status='confirmed', pickup_offset_min=0)
        r1 = make_reservation(base, o1, status='scheduled', start_offset_min=0, duration_min=60)

        o2 = make_order(base, status='pending', pickup_offset_min=70)
        make_reservation(base, o2, status='scheduled', start_offset_min=70, duration_min=60)

        max_min = order_service.max_extend_minutes(o1)
        # gap=10 минут, EXTEND_MINUTES=15 → cap = min(15, 10) = 10
        assert max_min == 10

    def test_extend_moves_pickup_and_end(self, base):
        o = make_order(base, status='confirmed', pickup_offset_min=10)
        r = make_reservation(base, o, status='scheduled', start_offset_min=10, duration_min=60)
        old_pickup = o.pickup_time
        old_end = r.end_time

        applied = order_service.extend(o)
        assert applied == 15  # дефолт EXTEND_MINUTES
        db.session.refresh(o); db.session.refresh(r)
        assert (o.pickup_time - old_pickup) == timedelta(minutes=15)
        assert (r.end_time - old_end) == timedelta(minutes=15)

    def test_extend_zero_when_no_room(self, base):
        # Соседняя бронь сразу после нашей — продлевать некуда
        o1 = make_order(base, status='confirmed', pickup_offset_min=0)
        make_reservation(base, o1, status='scheduled', start_offset_min=0, duration_min=60)

        o2 = make_order(base, status='pending', pickup_offset_min=62)
        make_reservation(base, o2, status='scheduled', start_offset_min=62, duration_min=60)

        # gap = 2 мин < MIN_USEFUL_EXTEND_MINUTES (5)
        applied = order_service.extend(o1)
        assert applied == 0


# ───────── reservation_repository.has_conflict / next_after ─────────

class TestReservationConflicts:
    def test_overlapping_intervals_conflict(self, base):
        o = make_order(base, status='confirmed')
        make_reservation(base, o, status='scheduled', start_offset_min=10, duration_min=30)
        now = now_utc_naive()
        # Окно 20..40 минут — пересекается с 10..40
        assert reservation_repository.has_conflict(
            base['table'].id,
            now + timedelta(minutes=20),
            now + timedelta(minutes=40),
        ) is True

    def test_adjacent_intervals_no_conflict(self, base):
        # Бронь 0..30, новая 30..60 — стык, без пересечения
        o = make_order(base, status='confirmed')
        make_reservation(base, o, status='scheduled', start_offset_min=0, duration_min=30)
        now = now_utc_naive()
        assert reservation_repository.has_conflict(
            base['table'].id,
            now + timedelta(minutes=30),
            now + timedelta(minutes=60),
        ) is False

    def test_cancelled_reservation_does_not_conflict(self, base):
        o = make_order(base, status='confirmed')
        make_reservation(base, o, status='cancelled',
                          start_offset_min=10, duration_min=30)
        now = now_utc_naive()
        assert reservation_repository.has_conflict(
            base['table'].id,
            now + timedelta(minutes=15),
            now + timedelta(minutes=25),
        ) is False

    def test_next_after_finds_closest(self, base):
        # Три брони, ищем следующую после now+50мин
        o1 = make_order(base, status='pending', pickup_offset_min=10)
        make_reservation(base, o1, start_offset_min=10, duration_min=20)
        o2 = make_order(base, status='pending', pickup_offset_min=60)
        r2 = make_reservation(base, o2, start_offset_min=60, duration_min=30)
        o3 = make_order(base, status='pending', pickup_offset_min=120)
        make_reservation(base, o3, start_offset_min=120, duration_min=30)

        now = now_utc_naive()
        nxt = reservation_repository.next_after(base['table'].id, now + timedelta(minutes=50))
        assert nxt is not None
        assert nxt.id == r2.id
