"""shift existing naive datetimes from MSK to UTC

Revision ID: b2c3d4_utc
Revises: a1b2c3_paid
Create Date: 2026-04-30

Раньше datetime'ы хранились как naive local (MSK). Теперь конвенция —
naive UTC. Чтобы старые записи не «прыгнули» на 3 часа вперёд при
отображении (UTC→MSK конверсия даст +3ч), вычитаем 3 часа из всех
существующих datetime-полей: orders.pickup_time, orders.created_at,
reservations.start_time, reservations.end_time, reservations.created_at,
users.created_at.

Однократная миграция — после неё все новые записи уже пишутся как UTC.
"""
from alembic import op


revision = 'b2c3d4_utc'
down_revision = 'a1b2c3_paid'
branch_labels = None
depends_on = None


# SQLite-совместимый синтаксис (datetime(col, '-3 hours')).
# Для PostgreSQL потребуется заменить на col - INTERVAL '3 hours'.
SHIFTS = [
    ("orders",       "pickup_time"),
    ("orders",       "created_at"),
    ("reservations", "start_time"),
    ("reservations", "end_time"),
    ("reservations", "created_at"),
    ("users",        "created_at"),
]


def upgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name
    for table, col in SHIFTS:
        if dialect == 'sqlite':
            op.execute(
                f"UPDATE {table} SET {col} = datetime({col}, '-3 hours') "
                f"WHERE {col} IS NOT NULL"
            )
        else:
            op.execute(
                f"UPDATE {table} SET {col} = {col} - INTERVAL '3 hours' "
                f"WHERE {col} IS NOT NULL"
            )


def downgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name
    for table, col in SHIFTS:
        if dialect == 'sqlite':
            op.execute(
                f"UPDATE {table} SET {col} = datetime({col}, '+3 hours') "
                f"WHERE {col} IS NOT NULL"
            )
        else:
            op.execute(
                f"UPDATE {table} SET {col} = {col} + INTERVAL '3 hours' "
                f"WHERE {col} IS NOT NULL"
            )
