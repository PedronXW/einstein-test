"""Repositório vetorial (pgvector): chunks de arquivos."""

from typing import Any, Protocol

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from einstein_test.models.file import File
from einstein_test.models.file_chunk import EMBEDDING_DIM, FileChunk


class VectorRepository(Protocol):
    def insert_chunks(
        self, file_id: int, chunks: list[dict[str, Any]]
    ) -> list[int]: ...
    def get_chunks(self, file_id: int) -> list[FileChunk]: ...
    def delete_chunks(self, file_id: int) -> None: ...
    def search_similar(
        self, embedding: list[float], chat_id: int, top_k: int = 4
    ) -> list[FileChunk]: ...


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

    def search_similar(
        self, embedding: list[float], chat_id: int, top_k: int = 4
    ) -> list[FileChunk]:
        """Busca os chunks mais similares (cosine) dos arquivos do chat."""
        if self.session.get_bind().dialect.name == "sqlite":
            from einstein_test.vector.similarity import cosine_similarity_search

            rows = (
                select(FileChunk)
                .join(File, File.id == FileChunk.file_id)
                .where(
                    File.chat_id == chat_id,
                    File.deleted_at.is_(None),
                )
            )
            return cosine_similarity_search(
                query=embedding,
                rows=list(self.session.scalars(rows)),
                top_k=top_k,
            )
        stmt = (
            select(FileChunk)
            .join(File, File.id == FileChunk.file_id)
            .where(
                File.chat_id == chat_id,
                File.deleted_at.is_(None),
            )
            .order_by(FileChunk.embedding.cosine_distance(embedding))
            .limit(top_k)
        )
        return list(self.session.scalars(stmt))