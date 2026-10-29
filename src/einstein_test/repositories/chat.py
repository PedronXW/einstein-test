"""Repositório de Chat: Protocol + implementação SQLAlchemy."""

from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from einstein_test.models.chat import Chat


class ChatRepository(Protocol):
    def create(
        self, user_id: int, name: str, description: str | None = None
    ) -> Chat: ...
    def get_by_id(self, chat_id: int, user_id: int) -> Chat | None: ...
    def list(
        self,
        user_id: int,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Chat]: ...
    def count(self, user_id: int) -> int: ...
    def delete(self, chat_id: int) -> None: ...


class ChatRepositorySQLAlchemy:
    """Implementação SQLAlchemy (soft delete; escopo por dono)."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self, user_id: int, name: str, description: str | None = None
    ) -> Chat:
        chat = Chat(user_id=user_id, name=name, description=description)
        self.session.add(chat)
        self.session.flush()
        self.session.refresh(chat)
        return chat

    def get_by_id(self, chat_id: int, user_id: int) -> Chat | None:
        stmt = select(Chat).where(
            Chat.id == chat_id,
            Chat.user_id == user_id,
            Chat.deleted_at.is_(None),
        )
        return self.session.scalar(stmt)

    def list(
        self,
        user_id: int,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Chat]:
        stmt = (
            select(Chat)
            .where(Chat.user_id == user_id, Chat.deleted_at.is_(None))
            .order_by(Chat.created_at.desc(), Chat.id.desc())
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        if offset is not None:
            stmt = stmt.offset(offset)
        return list(self.session.scalars(stmt))

    def count(self, user_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(Chat)
            .where(Chat.user_id == user_id, Chat.deleted_at.is_(None))
        )
        return int(self.session.scalar(stmt) or 0)

    def delete(self, chat_id: int) -> None:
        chat = self.session.get(Chat, chat_id)
        if chat is not None:
            chat.deleted_at = datetime.now(UTC)
            self.session.flush()