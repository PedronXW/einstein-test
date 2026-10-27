"""Repositório vetorial (pgvector): chunks de arquivos."""

from typing import Any, Protocol

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from einstein_test.models.file_chunk import EMBEDDING_DIM, FileChunk


class VectorRepository(Protocol):
    def insert_chunks(
        self, file_id: int, chunks: list[dict[str, Any]]
    ) -> list[int]: ...
    def get_chunks(self, file_id: int) -> list[FileChunk]: ...
    def delete_chunks(self, file_id: int) -> None: ...


class VectorRepositorySQLAlchemy:
    """Implementação SQLAlchemy + pgvector."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def insert_chunks(
        self, file_id: int, chunks: list[dict[str, Any]]
    ) -> list[int]:
        if not chunks:
            return []
        rows = [
            {
                "file_id": file_id,
                "chunk_index": chunk["index"],
                "content": chunk["content"],
                "embedding": chunk["embedding"],
            }
            for chunk in chunks
        ]
        stmt = insert(FileChunk).returning(FileChunk.id)
        ids = [row[0] for row in self.session.execute(stmt, rows)]
        self.session.commit()
        return ids

    def get_chunks(self, file_id: int) -> list[FileChunk]:
        stmt = (
            select(FileChunk)
            .where(FileChunk.file_id == file_id)
            .order_by(FileChunk.chunk_index)
        )
        return list(self.session.scalars(stmt))

    def delete_chunks(self, file_id: int) -> None:
        stmt = delete(FileChunk).where(FileChunk.file_id == file_id)
        self.session.execute(stmt)
        self.session.commit()