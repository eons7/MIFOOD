from werkzeug.security import generate_password_hash, check_password_hash
from app.models.user import User
from app.repositories import user_repository


def set_password(user: User, password: str) -> None:
    user.password_hash = generate_password_hash(password)


def verify_password(user: User, password: str) -> bool:
    return check_password_hash(user.password_hash, password)


def register(name: str, email: str, password: str) -> User:
    user = User(name=name, email=email)
    set_password(user, password)
    user_repository.save(user)
    return user
