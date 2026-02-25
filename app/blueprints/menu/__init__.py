from flask import Blueprint
menu_bp = Blueprint("menu", __name__, url_prefix="/menu")
from . import routes  # noqa
