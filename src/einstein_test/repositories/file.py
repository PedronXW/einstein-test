"""Repositório de File: Protocol + implementação SQLAlchemy."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from einstein_test.models.file import File


class FileRepository(Protocol):
    def create(
        self,
        chat_id: int,
        name: str,
        url: str,
        type: str | None = None,
        size: int = 0,
    ) -> File: ...
    def get_by_id(self, file_id: int) -> File | None: ...
    def list(self, chat_id: int) -> list[File]: ...
    def update_chunk_ids(
        self, file_id: int, chunk_ids: list[int], vector_reference: str
    ) -> None: ...
    def delete(self, file_id: int) -> None: ...


class FileRepositorySQLAlchemy:
    """Implementação SQLAlchemy (soft delete)."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        chat_id: int,
        name: str,
        url: str,
        type: str | None = None,
        size: int = 0,
    ) -> File:
        file_ = File(chat_id=chat_id, name=name, url=url, type=type, size=size)
        self.session.add(file_)
        self.session.flush()
        self.session.refresh(file_)
        return file_

    def get_by_id(self, file_id: int) -> File | None:
        stmt = select(File).where(
            File.id == file_id, File.deleted_at.is_(None)
        )
        return self.session.scalar(stmt)

    def list(self, chat_id: int) -> list[File]:
        stmt = (
            select(File)
            .where(
                File.chat_id == chat_id,
                File.deleted_at.is_(None),
            )
            .order_by(File.created_at.desc())
        )
        return list(self.session.scalars(stmt))

    def update_chunk_ids(
        self, file_id: int, chunk_ids: list[int], vector_reference: str
    ) -> None:
        file_ = self.session.get(File, file_id)
        if file_ is not None:
            file_.chunk_ids = chunk_ids
            file_.vector_reference = vector_reference
            self.session.flush()

    def delete(self, file_id: int) -> None:
        file_ = self.session.get(File, file_id)
        if file_ is not None:
            file_.deleted_at = datetime.now(UTC)
            self.session.flush()