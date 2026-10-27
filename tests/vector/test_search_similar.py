"""Testes TDD da feature F-011 (AC-001: busca por similaridade).

Valida a busca vetorial por similaridade (cosine) filtrada por chat,
top_k e o cálculo de cosine em Python (fallback SQLite / fake).
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from einstein_test.db.base import Base
from einstein_test.models.file import File
from einstein_test.models.file_chunk import FileChunk
from einstein_test.vector.repository import VectorRepositorySQLAlchemy
from einstein_test.vector.similarity import cosine_similarity, cosine_similarity_search


def _setup(engine):
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        chat = __import__("einstein_test.models.chat", fromlist=["Chat"]).Chat(
            name="Chat"
        )
        session.add(chat)
        session.flush()
        f1 = File(chat_id=chat.id, name="a.txt", url="s3://b/a.txt")
        f2 = File(chat_id=chat.id, name="b.txt", url="s3://b/b.txt")
        session.add_all([f1, f2])
        session.flush()
        chat2 = __import__("einstein_test.models.chat", fromlist=["Chat"]).Chat(
            name="Outro"
        )
        session.add(chat2)
        session.flush()
        f3 = File(chat_id=chat2.id, name="c.txt", url="s3://b/c.txt")
        session.add(f3)
        session.flush()
        vrepo = VectorRepositorySQLAlchemy(session)
        vrepo.insert_chunks(
            f1.id,
            [
                {"index": 0, "content": "sobre gorilas", "embedding": [1.0, 0.0, 0.0]},
                {"index": 1, "content": "sobre zebras", "embedding": [0.0, 1.0, 0.0]},
            ],
        )
        vrepo.insert_chunks(
            f2.id,
            [
                {"index": 0, "content": "mais gorilas", "embedding": [0.9, 0.1, 0.0]},
                {"index": 1, "content": "sobre elefantes", "embedding": [0.0, 0.0, 1.0]},
            ],
        )
        vrepo.insert_chunks(
            f3.id,
            [
                {"index": 0, "content": "gorila de outro chat", "embedding": [0.99, 0.01, 0.0]},
            ],
        )
        return chat.id, chat2.id, f1.id, f2.id, f3.id


def test_ac001_cosine_similarity_basic():
    assert cosine_similarity([1.0, 0.0, 0.0], [1.0, 0.0, 0.0]) == pytest.approx(1.0)
    assert cosine_similarity([1.0, 0.0, 0.0], [0.0, 1.0, 0.0]) == pytest.approx(0.0)


def test_ac001_cosine_similarity_ordering():
    query = [1.0, 0.0, 0.0]
    ranked = sorted(
        [([0.9, 0.1, 0.0], "a"), ([0.0, 1.0, 0.0], "b"), ([0.99, 0.01, 0.0], "c")],
        key=lambda item: cosine_similarity(query, item[0]),
        reverse=True,
    )
    assert [c for _, c in ranked] == ["c", "a", "b"]


def test_ac001_cosine_similarity_search_returns_top_k_and_chat_only():
    engine = create_engine("sqlite:///:memory:")
    chat_id, other_chat_id, f1_id, f2_id, f3_id = _setup(engine)
    with Session(engine) as session:
        vrepo = VectorRepositorySQLAlchemy(session)
        query = [0.95, 0.05, 0.0]  # perto de gorilas
        # impl real de busca (filtra por chat via join)
        chunks = vrepo.search_similar(
            embedding=query,
            chat_id=chat_id,
            top_k=2,
        )
        assert len(chunks) == 2
        assert all(c.file_id in (f1_id, f2_id) for c in chunks)
        contents = [c.content for c in chunks]
        assert "gorilas" in " ".join(contents), "chunks de gorila primeiro"
        # ordem relativa: chunk mais similar (sobre gorilas, emb [1,0,0]) primeiro
        assert contents[0] == "sobre gorilas", (
            "chunk mais próximo do query vem primeiro"
        )
        # chat diferente não entra
        other = vrepo.search_similar(
            embedding=[1.0, 0.0, 0.0],
            chat_id=other_chat_id,
            top_k=4,
        )
        assert all(c.file_id == f3_id for c in other)
    engine.dispose()


def test_ac001_cosine_similarity_search_top_k_limits():
    engine = create_engine("sqlite:///:memory:")
    chat_id, _, _, _, _ = _setup(engine)
    with Session(engine) as session:
        vrepo = VectorRepositorySQLAlchemy(session)
        chunks = cosine_similarity_search(
            query=[1.0, 0.0, 0.0], rows=vrepo.get_chunks(chat_id), top_k=1
        )
        assert len(chunks) == 1
    engine.dispose()


def test_ac001_cosine_similarity_search_empty():
    assert cosine_similarity_search([1.0, 0.0], [], top_k=4) == []


def test_ac001_search_similar_method_on_repo():
    from einstein_test.vector import VectorRepository

    assert hasattr(VectorRepository, "search_similar")