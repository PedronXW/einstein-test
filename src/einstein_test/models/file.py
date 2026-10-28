"""Model File."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import JSON, BigInteger, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from einstein_test.db.base import Base
from einstein_test.models.mixin import TimestampMixin

if TYPE_CHECKING:
    from einstein_test.models.chat import Chat


class File(TimestampMixin, Base):
    __tablename__ = "files"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    type: Mapped[str | None] = mapped_column(String(127), nullable=True)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chats.id"), nullable=False, index=True
    )
    chunk_ids: Mapped[list[int]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=list,
        server_default=text("'[]'"),
    )
    vector_reference: Mapped[str | None] = mapped_column(
        String(36), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending",
        server_default=text("'pending'"),
    )
    error_detail: Mapped[str | None] = mapped_column(
        String(1024), nullable=True
    )

    chat: Mapped["Chat"] = relationship(back_populates="files")
