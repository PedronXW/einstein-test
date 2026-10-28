"""Model Message."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from einstein_test.db.base import Base
from einstein_test.models.mixin import TimestampMixin

if TYPE_CHECKING:
    from einstein_test.models.chat import Chat


class Message(TimestampMixin, Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chats.id"), nullable=False, index=True
    )

    chat: Mapped["Chat"] = relationship(back_populates="messages")
