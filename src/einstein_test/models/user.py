"""Model User."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from einstein_test.db.base import Base
from einstein_test.models.mixin import TimestampMixin

if TYPE_CHECKING:
    from einstein_test.models.chat import Chat


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    model: Mapped[str | None] = mapped_column(
        String(127), nullable=True, default="azure/gpt-5-mini"
    )

    chats: Mapped[list["Chat"]] = relationship(back_populates="owner")
