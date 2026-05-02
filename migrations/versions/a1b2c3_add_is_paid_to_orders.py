"""add is_paid to orders + migrate paid status

Revision ID: a1b2c3_paid
Revises: ed82fa747c3f
Create Date: 2026-04-30

Раньше 'paid' было кухонным статусом — это путало FSM.
Делим на ось:
  - status (кухня): pending → confirmed → ready → completed (+ cancelled / expired)
  - is_paid (платёж): boolean, обновляется независимо

Старые заказы со status='paid' интерпретируем как «оплачен онлайн до того
как кухня приняла»: status='pending', is_paid=True. Кухня сама решит когда
переводить в confirmed.
"""
from alembic import op
import sqlalchemy as sa


revision = 'a1b2c3_paid'
down_revision = 'ed82fa747c3f'
branch_labels = None
depends_on = None


def upgrade():
    # 1) Добавляем колонку с server_default=False, чтобы не упасть на NOT NULL
    with op.batch_alter_table('orders') as batch_op:
        batch_op.add_column(sa.Column(
            'is_paid', sa.Boolean(), nullable=False,
            server_default=sa.false(),
        ))

    # 2) Переносим существующие 'paid'-заказы:
    #    is_paid = True, status = 'pending' (кухня заново решит когда принять)
    op.execute("UPDATE orders SET is_paid = TRUE, status = 'pending' WHERE status = 'paid'")

    # 3) Снимаем server_default — дальше дефолт ставит модель
    with op.batch_alter_table('orders') as batch_op:
        batch_op.alter_column('is_paid', server_default=None)


def downgrade():
    # Откат: восстанавливаем 'paid' для is_paid=True заказов в статусе pending.
    # Не идеально (теряем confirmed/ready/completed с is_paid=True), но обратно
    # уместить два поля в одно невозможно без потерь.
    op.execute("UPDATE orders SET status = 'paid' WHERE is_paid = TRUE AND status = 'pending'")
    with op.batch_alter_table('orders') as batch_op:
        batch_op.drop_column('is_paid')
