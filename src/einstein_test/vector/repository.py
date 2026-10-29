"""Repositório vetorial (pgvector): chunks de arquivos."""

from typing import Any, Protocol

from sqlalchemy import Select, delete, insert, select
from sqlalchemy.orm import Session

from einstein_test.models.file import File
from einstein_test.models.file_chunk import FileChunk
from einstein_test.vector.similarity import per_file_top_k_search

# Teto de candidatos do pool KNN (tuning — fonte única).
MAX_CANDIDATES = 200


def _candidate_limit(num_files: int, chunks_per_file: int, max_chunks: int) -> int:
    """Tamanho do pool KNN: garante ao menos `max_chunks`, cobre o top-por-
    arquivo (`num_files * chunks_per_file`) e respeita o teto `MAX_CANDIDATES`."""
    return min(max(num_files * chunks_per_file, max_chunks), MAX_CANDIDATES)


def _knn_statement(
    embedding: list[float],
    file_ids: list[int],
    candidate_limit: int,
) -> Select[tuple[FileChunk]]:
    """Statement KNN do Postgres — forma reconhecida pelo planner como scan
    do índice HNSW (`ORDER BY embedding <=> :q` + `LIMIT`), filtrado pelos
    arquivos do chat."""
    return (
        select(FileChunk)
        .where(FileChunk.file_id.in_(file_ids))
        .order_by(FileChunk.embedding.cosine_distance(embedding))
        .limit(candidate_limit)
    )


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

        PostgreSQL: candidate-pool KNN (`ORDER BY embedding <=> :q` + `LIMIT`,
        forma que o planner pode usar o índice HNSW) filtrado pelos arquivos do
        chat, e re-rank em Python (`per_file_top_k_search`). A semântica é a do
        fallback quando o pool contém o top-`chunks_per_file` de cada arquivo;
        é uma **aproximação** quando um arquivo domina o pool (chunks além do
        top-`MAX_CANDIDATES` global não participam do re-rank).
        SQLite: fallback em Python sobre todo o chat (sem operador).
        """
        if self.session.get_bind().dialect.name == "sqlite":
            base = (
                select(FileChunk)
                .join(File, File.id == FileChunk.file_id)
                .where(
                    File.chat_id == chat_id,
                    File.deleted_at.is_(None),
                )
            )
            return per_file_top_k_search(
                query=embedding,
                rows=list(self.session.scalars(base)),
                chunks_per_file=chunks_per_file,
                max_chunks=max_chunks,
            )
        file_ids = list(
            self.session.scalars(
                select(File.id).where(
                    File.chat_id == chat_id,
                    File.deleted_at.is_(None),
                )
            )
        )
        if not file_ids:
            return []
        candidate_limit = _candidate_limit(
            num_files=len(file_ids),
            chunks_per_file=chunks_per_file,
            max_chunks=max_chunks,
        )
        candidates = list(
            self.session.scalars(
                _knn_statement(embedding, file_ids, candidate_limit)
            )
        )
        return per_file_top_k_search(
            query=embedding,
            rows=candidates,
            chunks_per_file=chunks_per_file,
            max_chunks=max_chunks,
        )
