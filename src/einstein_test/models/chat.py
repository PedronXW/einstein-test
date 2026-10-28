"""Model Chat."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from einstein_test.db.base import Base
from einstein_test.models.mixin import TimestampMixin

if TYPE_CHECKING:
    from einstein_test.models.file import File
    from einstein_test.models.message import Message
    from einstein_test.models.user import User


class Chat(TimestampMixin, Base):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    owner: Mapped["User"] = relationship(back_populates="chats")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="chat", cascade="all, delete-orphan"
    )
    files: Mapped[list["File"]] = relationship(
        back_populates="chat", cascade="all, delete-orphan"
    )