"""add payment_id to orders for YooKassa integration

Revision ID: c3d4e5_payment
Revises: b2c3d4_utc
Create Date: 2026-05-03
"""
from alembic import op
import sqlalchemy as sa


revision = 'c3d4e5_payment'
down_revision = 'b2c3d4_utc'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('orders') as batch_op:
        batch_op.add_column(sa.Column('payment_id', sa.String(length=64), nullable=True))
        batch_op.create_index('ix_orders_payment_id', ['payment_id'])


def downgrade():
    with op.batch_alter_table('orders') as batch_op:
        batch_op.drop_index('ix_orders_payment_id')
        batch_op.drop_column('payment_id')
