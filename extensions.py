# extensions.py
# Объект db создаётся здесь, отдельно от app,
# чтобы избежать циклических импортов между моделями и приложением.

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
