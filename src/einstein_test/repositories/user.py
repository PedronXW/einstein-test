"""Repositório de User: Protocol + implementação SQLAlchemy.

O repositório persiste o hash já pronto — a política criptográfica (bcrypt)
vive em `einstein_test.security`.
"""

from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from einstein_test.models.user import User


class UserRepository(Protocol):
    def create(self, email: str, password_hash: str) -> User: ...
    def get_by_email(self, email: str) -> User | None: ...


class UserRepositorySQLAlchemy:
    """Implementação SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, email: str, password_hash: str) -> User:
        user = User(email=email, password_hash=password_hash)
        self.session.add(user)
        self.session.flush()
        self.session.refresh(user)
        return user

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return self.session.scalar(stmt)