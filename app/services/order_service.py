from app.models.order import Order
from app.repositories import order_repository

CANCELLABLE_STATUSES = ['pending', 'confirmed']


def calculate_total(order: Order) -> float:
    total = sum(item.quantity * item.menu_item.price for item in order.order_items)
    order.total_price = total
    return total


def can_cancel(order: Order) -> bool:
    return order.status in CANCELLABLE_STATUSES


def cancel(order: Order) -> None:
    order.status = 'cancelled'
    order_repository.save(order)
