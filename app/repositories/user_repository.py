from app.extensions import db
from app.models.user import User


def get_by_id(user_id: int) -> User | None:
    return db.session.get(User, user_id)


def get_by_email(email: str) -> User | None:
    return User.query.filter_by(email=email).first()


def exists_by_email(email: str) -> bool:
    return User.query.filter_by(email=email).count() > 0


def save(user: User) -> User:
    db.session.add(user)
    db.session.commit()
    return user
