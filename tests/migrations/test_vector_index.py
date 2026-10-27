"""Testes TDD da feature F-017 (índice HNSW no pgvector).

Valida que a migration emite CREATE INDEX ... USING hnsw (vector_cosine_ops)
e que a busca vetorial (search_similar) continua funcionando.
"""

import os
import pathlib
import subprocess

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from einstein_test.db.base import Base
from einstein_test.models.file import File
from einstein_test.models.file_chunk import FileChunk
from einstein_test.models.user import User
from einstein_test.vector.repository import VectorRepositorySQLAlchemy

ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_ac001_migration_emits_hnsw_index():
    env = dict(os.environ)
    env["DATABASE_URL"] = "postgresql://einstein:einstein@localhost:5432/einstein"
    proc = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head", "--sql"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "USING hnsw" in proc.stdout, "índice usa hnsw"
    assert (
        "embedding vector_cosine_ops" in proc.stdout
        or "embedding) vector_cosine_ops" in proc.stdout
        or "vector_cosine_ops" in proc.stdout
    ), "índice usa vector_cosine_ops"


def test_ac001_index_name_present():
    env = dict(os.environ)
    env["DATABASE_URL"] = "postgresql://einstein:einstein@localhost:5432/einstein"
    proc = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head", "--sql"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "ix_file_chunks_embedding_hnsw" in proc.stdout, "índice nomeado"


def test_ac002_search_similar_still_works_after_index():
    from einstein_test.models.chat import Chat

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        owner = User(email="dono@b.com", password_hash="x")
        session.add(owner)
        session.flush()
        chat = Chat(user_id=owner.id, name="Chat")
        session.add(chat)
        session.flush()
        f = File(chat_id=chat.id, name="a.txt", url="s3://b/a.txt")
        session.add(f)
        session.flush()
        vrepo = VectorRepositorySQLAlchemy(session)
        vrepo.insert_chunks(
            f.id,
            [
                {"index": 0, "content": "sobre gorilas", "embedding": [1.0, 0.0, 0.0]},
                {"index": 1, "content": "sobre zebras", "embedding": [0.0, 1.0, 0.0]},
            ],
        )
        chunks = vrepo.search_similar(
            embedding=[0.9, 0.1, 0.0], chat_id=chat.id, max_chunks=1
        )
        assert len(chunks) == 1
        assert "gorilas" in chunks[0].content, "busca preservada (fallback sqlite)"
    engine.dispose()