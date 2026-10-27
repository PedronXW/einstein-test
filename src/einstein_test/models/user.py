"""Model User."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from einstein_test.db.base import Base
from einstein_test.models.mixin import TimestampMixin

DEFAULT_USER_MODEL = "azure/gpt-5-mini"


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    model: Mapped[str | None] = mapped_column(
        String(127), nullable=True, default=DEFAULT_USER_MODEL
    )

    chats: Mapped[list["Chat"]] = relationship(back_populates="owner")