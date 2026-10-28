"""Repositório vetorial (pgvector): chunks de arquivos."""

from typing import Any, Protocol

from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import Session, aliased

from einstein_test.models.file import File
from einstein_test.models.file_chunk import FileChunk


class VectorRepository(Protocol):
    def insert_chunks(
        self, file_id: int, chunks: list[dict[str, Any]]
    ) -> list[int]: ...
    def get_chunks(self, file_id: int) -> list[FileChunk]: ...
    def delete_chunks(self, file_id: int) -> None: ...
    def search_similar(
        self,
        embedding: list[float],
        chat_id: int,
        chunks_per_file: int,
        max_chunks: int,
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
        self.session.flush()
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
        self.session.flush()

    def search_similar(
        self,
        embedding: list[float],
        chat_id: int,
        chunks_per_file: int,
        max_chunks: int,
    ) -> list[FileChunk]:
        """Busca os chunks mais similares por arquivo do chat.

        PostgreSQL: janela ROW_NUMBER particionada por file_id, limitando a
        `chunks_per_file` por arquivo, reordenada por similaridade e truncada
        em `max_chunks`. SQLite: fallback em Python (mesma semântica).
        """
        base = (
            select(FileChunk)
            .join(File, File.id == FileChunk.file_id)
            .where(
                File.chat_id == chat_id,
                File.deleted_at.is_(None),
            )
        )
        if self.session.get_bind().dialect.name == "sqlite":
            from einstein_test.vector.similarity import per_file_top_k_search

            return per_file_top_k_search(
                query=embedding,
                rows=list(self.session.scalars(base)),
                chunks_per_file=chunks_per_file,
                max_chunks=max_chunks,
            )
        distance = FileChunk.embedding.cosine_distance(embedding)
        rn = func.row_number().over(
            partition_by=FileChunk.file_id,
            order_by=distance,
        ).label("rn")
        sub = (
            select(FileChunk, rn)
            .join(File, File.id == FileChunk.file_id)
            .where(
                File.chat_id == chat_id,
                File.deleted_at.is_(None),
            )
            .subquery()
        )
        aliased_chunk = aliased(FileChunk, sub)
        stmt = (
            select(aliased_chunk)
            .where(sub.c.rn <= chunks_per_file)
            .order_by(aliased_chunk.embedding.cosine_distance(embedding))
            .limit(max_chunks)
        )
        return list(self.session.scalars(stmt))