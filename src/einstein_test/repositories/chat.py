"""Repositório de Chat: Protocol + implementação SQLAlchemy."""

from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from einstein_test.models.chat import Chat


class ChatRepository(Protocol):
    def create(self, name: str, description: str | None = None) -> Chat: ...
    def get_by_id(self, chat_id: int) -> Chat | None: ...
    def list(self) -> list[Chat]: ...
    def delete(self, chat_id: int) -> None: ...


class ChatRepositorySQLAlchemy:
    """Implementação SQLAlchemy (soft delete)."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, name: str, description: str | None = None) -> Chat:
        chat = Chat(name=name, description=description)
        self.session.add(chat)
        self.session.commit()
        self.session.refresh(chat)
        return chat

    def get_by_id(self, chat_id: int) -> Chat | None:
        stmt = select(Chat).where(
            Chat.id == chat_id, Chat.deleted_at.is_(None)
        )
        return self.session.scalar(stmt)

    def list(self) -> list[Chat]:
        stmt = (
            select(Chat)
            .where(Chat.deleted_at.is_(None))
            .order_by(Chat.created_at.desc())
        )
        return list(self.session.scalars(stmt))

    def delete(self, chat_id: int) -> None:
        chat = self.session.get(Chat, chat_id)
        if chat is not None:
            chat.deleted_at = datetime.now(UTC)
            self.session.commit()