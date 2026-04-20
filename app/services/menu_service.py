from app.models.menu import MenuItem
from app.repositories import menu_repository


def toggle_availability(item: MenuItem) -> None:
    item.is_available = not item.is_available
    menu_repository.save_item(item)
