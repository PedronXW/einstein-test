"""Model Message."""

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixin import TimestampMixin


class Message(TimestampMixin, Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chats.id"), nullable=False, index=True
    )

    chat: Mapped["Chat"] = relationship(back_populates="messages")