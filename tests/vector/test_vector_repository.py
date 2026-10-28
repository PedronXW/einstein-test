"""Testes TDD da feature F-010 (AC-004: repositório vetorial pgvector).

Valida a tabela file_chunks (model FileChunk) e o VectorRepository
(Protocol + implementação SQLAlchemy com pgvector).
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from einstein_test.db.base import Base
from einstein_test.models.file_chunk import FileChunk
from einstein_test.repositories import VectorRepository, VectorRepositorySQLAlchemy


@pytest.fixture
def engine():
    e = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(e)
    yield e
    e.dispose()


@pytest.fixture
def repo(engine):
    with Session(engine) as session:
        yield VectorRepositorySQLAlchemy(session), session


def test_ac004_table_file_chunks_registered():
    assert "file_chunks" in Base.metadata.tables, "tabela file_chunks registrada"


def test_ac004_file_chunk_columns():
    cols = {c.name for c in FileChunk.__table__.columns}
    assert {"id", "file_id", "chunk_index", "content", "embedding"} <= cols
    assert FileChunk.__table__.c.file_id.primary_key is False
    assert FileChunk.__table__.c.chunk_index.nullable is False


def test_ac004_file_chunk_fk():
    fk = list(FileChunk.__table__.c.file_id.foreign_keys)
    assert len(fk) == 1
    assert fk[0].column.table.name == "files", "FileChunk.file_id -> files.id"


def test_ac004_vector_repository_protocol():
    assert hasattr(VectorRepository, "insert_chunks")
    assert hasattr(VectorRepository, "get_chunks")


def test_ac004_insert_and_get_chunks(repo):
    vector_repo, session = repo
    chunks = [
        {"index": 0, "content": "primeiro chunk", "embedding": [1.0, 2.0, 3.0]},
        {"index": 1, "content": "segundo chunk", "embedding": [4.0, 5.0, 6.0]},
    ]
    ids = vector_repo.insert_chunks(file_id=42, chunks=chunks)
    assert len(ids) == 2
    assert all(isinstance(i, int) for i in ids)

    got = vector_repo.get_chunks(file_id=42)
    assert len(got) == 2
    by_index = {c.chunk_index: c for c in got}
    assert by_index[0].content == "primeiro chunk"
    assert list(by_index[0].embedding) == [1.0, 2.0, 3.0]
    assert by_index[1].content == "segundo chunk"


def test_ac004_get_chunks_unknown_file(repo):
    vector_repo, session = repo
    assert vector_repo.get_chunks(file_id=999) == []


def test_ac004_insert_chunks_returns_ids_saved(repo):
    vector_repo, session = repo
    ids = vector_repo.insert_chunks(file_id=1, chunks=[{"index": 0, "content": "x", "embedding": [0.1] * 3}])
    got = vector_repo.get_chunks(file_id=1)
    assert [c.id for c in got] == ids, "ids retornados persistem no banco"


def test_ac004_embedding_dimension_declared():
    col = FileChunk.__table__.c.embedding
    dim = getattr(col.type, "dim", None)
    assert dim == 1536, "embedding é vector(1536)"