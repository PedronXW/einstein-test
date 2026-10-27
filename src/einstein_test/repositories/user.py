"""Repositório de User: Protocol + implementação SQLAlchemy."""

from typing import Protocol

import bcrypt
from sqlalchemy import select
from sqlalchemy.orm import Session

from einstein_test.models.user import User


def hash_password(password: str) -> str:
    """Hash bcrypt da senha (salteado)."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verifica senha contra o hash bcrypt."""
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"), password_hash.encode("utf-8")
        )
    except ValueError:
        return False


class UserRepository(Protocol):
    def create(self, email: str, password: str) -> User: ...
    def get_by_email(self, email: str) -> User | None: ...


class UserRepositorySQLAlchemy:
    """Implementação SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, email: str, password: str) -> User:
        user = User(email=email, password_hash=hash_password(password))
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return self.session.scalar(stmt)