"""Repositório de Message: Protocol + implementação SQLAlchemy."""

from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from einstein_test.models.message import Message


class MessageRepository(Protocol):
    def create(
        self, chat_id: int, content: str, role: str | None = None
    ) -> Message: ...
    def get_by_id(self, message_id: int) -> Message | None: ...
    def list(self, chat_id: int) -> list[Message]: ...
    def delete(self, message_id: int) -> None: ...


class MessageRepositorySQLAlchemy:
    """Implementação SQLAlchemy (soft delete)."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self, chat_id: int, content: str, role: str | None = None
    ) -> Message:
        message = Message(chat_id=chat_id, content=content, role=role)
        self.session.add(message)
        self.session.flush()
        self.session.refresh(message)
        return message

    def get_by_id(self, message_id: int) -> Message | None:
        stmt = select(Message).where(
            Message.id == message_id, Message.deleted_at.is_(None)
        )
        return self.session.scalar(stmt)

    def list(self, chat_id: int) -> list[Message]:
        stmt = (
            select(Message)
            .where(
                Message.chat_id == chat_id,
                Message.deleted_at.is_(None),
            )
            .order_by(Message.created_at.asc(), Message.id.asc())
        )
        return list(self.session.scalars(stmt))

    def delete(self, message_id: int) -> None:
        message = self.session.get(Message, message_id)
        if message is not None:
            message.deleted_at = datetime.now(UTC)
            self.session.flush()