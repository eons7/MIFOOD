from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from app import db  # SQLAlchemy instance
from app.models.user import User

from . import auth_bp


@auth_bp.get("/login")
def login():
    return render_template("auth/login.html")


@auth_bp.post("/login")
def login_post():
    # На текущем этапе проект только “каркас”. Реальную проверку пароля
    # добавим позже, когда формы будут реализованы.
    flash("Вход пока не реализован. Перейдите к регистрации.", "warning")
    return redirect(url_for("auth.login"))


@auth_bp.get("/register")
def register():
    return render_template("auth/register.html")


@auth_bp.post("/register")
def register_post():
    # Заглушка: форма регистрации пока не заполнена.
    flash("Регистрация пока не реализована. Эта страница — заглушка.", "warning")
    return redirect(url_for("auth.register"))


@auth_bp.get("/logout")
def logout():
    if current_user.is_authenticated:
        logout_user()
    flash("Вы вышли из аккаунта.", "info")
    return redirect(url_for("home"))



