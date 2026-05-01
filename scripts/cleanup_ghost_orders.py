"""Удаление «призрачных» заказов: pending без брони.

Появлялись из-за бага в старом флоу — заказ коммитился до выбора стола,
если юзер уходил со страницы выбора, заказ оставался pending без брони.
После рефакторинга этого больше не происходит, но БД нужно почистить.

Запуск из корня проекта:
    python3 scripts/cleanup_ghost_orders.py        # сухой прогон, только список
    python3 scripts/cleanup_ghost_orders.py --yes  # реально удалить
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import or_

from app import create_app
from app.extensions import db
from app.models.order import Order, OrderItem
from app.models.reservation import Reservation


def main(dry_run: bool = True) -> None:
    app = create_app()
    with app.app_context():
        # Категория А: pending-заказы без брони (артефакт старого бажного флоу).
        ghosts_no_res = (
            Order.query
            .filter(Order.status == 'pending')
            .filter(~Order.reservation.has())
            .order_by(Order.created_at.asc())
            .all()
        )

        # Категория Б: заказы вообще без позиций (нечего отображать в составе).
        # Бывают артефактом тестов и недо-флоу. Чистим вместе со связанной бронью.
        empty_orders = (
            Order.query
            .filter(~Order.order_items.any())
            .order_by(Order.created_at.asc())
            .all()
        )

        all_targets = {o.id: o for o in ghosts_no_res}
        for o in empty_orders:
            all_targets[o.id] = o

        if not all_targets:
            print('Чистить нечего.')
            return

        print(f'Категория А (pending без брони): {len(ghosts_no_res)}')
        for o in ghosts_no_res:
            print(f'  #{o.id}  user={o.user_id}  created={o.created_at}  total={o.total_price}')
        print(f'Категория Б (без позиций): {len(empty_orders)}')
        for o in empty_orders:
            res_info = f'res #{o.reservation.id} [{o.reservation.status}]' if o.reservation else 'без брони'
            print(f'  #{o.id}  user={o.user_id}  status={o.status}  {res_info}')

        if dry_run:
            print('\nСухой прогон. Запусти с --yes, чтобы реально удалить.')
            return

        for o in all_targets.values():
            OrderItem.query.filter_by(order_id=o.id).delete()
            # Связанные брони — каскадим вручную, в модели нет cascade
            Reservation.query.filter_by(order_id=o.id).delete()
            db.session.delete(o)
        db.session.commit()
        print(f'\nУдалено заказов: {len(all_targets)}.')


if __name__ == '__main__':
    main(dry_run='--yes' not in sys.argv)
