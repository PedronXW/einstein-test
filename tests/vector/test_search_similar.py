"""Testes TDD da feature F-011 (AC-001: busca por similaridade).

Valida a busca vetorial por similaridade (cosine) filtrada por chat,
com semântica "2 chunks por arquivo + teto global (12)" e ordenação global.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from einstein_test.db.base import Base
from einstein_test.models.file import File
from einstein_test.models import User
from einstein_test.vector.repository import VectorRepositorySQLAlchemy
from einstein_test.vector.similarity import (
    cosine_similarity,
    cosine_similarity_search,
    per_file_top_k_search,
)


def _setup(engine):
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        owner = User(email="dono@b.com", password_hash="x")
        other = User(email="outro@b.com", password_hash="x")
        session.add_all([owner, other])
        session.flush()
        chat = __import__("einstein_test.models.chat", fromlist=["Chat"]).Chat(
            user_id=owner.id, name="Chat"
        )
        session.add(chat)
        session.flush()
        f1 = File(chat_id=chat.id, name="a.txt", url="s3://b/a.txt")
        f2 = File(chat_id=chat.id, name="b.txt", url="s3://b/b.txt")
        session.add_all([f1, f2])
        session.flush()
        chat2 = __import__("einstein_test.models.chat", fromlist=["Chat"]).Chat(
            user_id=other.id, name="Outro"
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
                {"index": 2, "content": "gorilas e bananas", "embedding": [0.9, 0.0, 0.1]},
            ],
        )
        vrepo.insert_chunks(
            f2.id,
            [
                {"index": 0, "content": "mais gorilas", "embedding": [0.98, 0.02, 0.0]},
                {"index": 1, "content": "sobre elefantes", "embedding": [0.0, 0.0, 1.0]},
                {"index": 2, "content": "gorilas gigantes", "embedding": [0.96, 0.0, 0.04]},
            ],
        )
        vrepo.insert_chunks(
            f3.id,
            [
                {"index": 0, "content": "gorila de outro chat", "embedding": [0.99, 0.01, 0.0]},
            ],
        )
        session.commit()
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


def test_ac001_search_filters_chat_only():
    engine = create_engine("sqlite:///:memory:")
    chat_id, other_chat_id, f1_id, f2_id, f3_id = _setup(engine)
    with Session(engine) as session:
        vrepo = VectorRepositorySQLAlchemy(session)
        query = [1.0, 0.0, 0.0]
        chunks = vrepo.search_similar(embedding=query, chat_id=chat_id)
        assert all(c.file_id in (f1_id, f2_id) for c in chunks)
        other = vrepo.search_similar(embedding=query, chat_id=other_chat_id)
        assert all(c.file_id == f3_id for c in other)
    engine.dispose()


def test_ac001_search_two_chunks_per_file():
    engine = create_engine("sqlite:///:memory:")
    chat_id, _, f1_id, f2_id, _ = _setup(engine)
    with Session(engine) as session:
        vrepo = VectorRepositorySQLAlchemy(session)
        query = [1.0, 0.0, 0.0]  # perto de gorilas (presente em f1 e f2)
        chunks = vrepo.search_similar(
            embedding=query, chat_id=chat_id, chunks_per_file=2, max_chunks=12
        )
        # 2 chunks de cada arquivo, mesmo com f1/f2 tendo 3 chunks cada
        assert len(chunks) == 4
        f1_chunks = [c for c in chunks if c.file_id == f1_id]
        f2_chunks = [c for c in chunks if c.file_id == f2_id]
        assert len(f1_chunks) == 2, "máximo 2 chunks por arquivo (f1)"
        assert len(f2_chunks) == 2, "máximo 2 chunks por arquivo (f2)"
    engine.dispose()


def test_ac001_search_orders_globally_by_similarity():
    engine = create_engine("sqlite:///:memory:")
    chat_id, _, f1_id, f2_id, _ = _setup(engine)
    with Session(engine) as session:
        vrepo = VectorRepositorySQLAlchemy(session)
        query = [1.0, 0.0, 0.0]
        chunks = vrepo.search_similar(
            embedding=query, chat_id=chat_id, chunks_per_file=2, max_chunks=12
        )
        contents = [c.content for c in chunks]
        # os mais similares de cada arquivo ("sobre gorilas" f1, "mais gorilas" f2)
        # devem vir primeiro, na ordem global
        assert contents[0] == "sobre gorilas", "mais similar global primeiro"
        assert "mais gorilas" in contents[:2]
    engine.dispose()


def test_ac001_search_max_chunks_cap():
    # 8 arquivos: os 6 primeiros relevantes (2 chunks de alta similaridade cada),
    # os 2 últimos irrelevantes (ambos os chunks com baixa similaridade).
    # Com 2 por arquivo + teto 12, os 6 relevantes (12 chunks) preenchem o teto
    # e os irrelevantes ficam de fora.
    rows = []
    for file_id in range(1, 7):  # 6 arquivos relevantes
        rows.append(
            type("Chunk", (), {"file_id": file_id, "content": f"f{file_id}-a", "embedding": [0.9, 0.1]})()
        )
        rows.append(
            type("Chunk", (), {"file_id": file_id, "content": f"f{file_id}-b", "embedding": [0.8, 0.2]})()
        )
    for file_id in range(7, 9):  # 2 arquivos irrelevantes
        rows.append(
            type("Chunk", (), {"file_id": file_id, "content": f"f{file_id}-x", "embedding": [0.01, 0.99]})()
        )
        rows.append(
            type("Chunk", (), {"file_id": file_id, "content": f"f{file_id}-y", "embedding": [0.02, 0.98]})()
        )
    res = per_file_top_k_search(
        query=[1.0, 0.0],
        rows=rows,
        chunks_per_file=2,
        max_chunks=12,
    )
    assert len(res) == 12, "teto max_chunks=12 respeitado"
    # os 12 chunks dos 6 arquivos relevantes preenchem o teto; os irrelevantes
    # (7,8) ficam de fora
    file_ids = {c.file_id for c in res}
    assert file_ids == {1, 2, 3, 4, 5, 6}, "prioriza os arquivos mais relevantes"


def test_ac001_search_single_chunk_file_returns_one():
    # arquivo com só 1 chunk: retorna 1 (não inventa segundo)
    rows = [
        type("Chunk", (), {"file_id": 1, "content": "único", "embedding": [0.9, 0.1]})(),
    ]
    res = per_file_top_k_search(query=[1.0, 0.0], rows=rows, chunks_per_file=2)
    assert len(res) == 1
    assert res[0].content == "único"


def test_ac001_cosine_similarity_search_still_works():
    rows = [
        type("Chunk", (), {"file_id": 1, "content": "a", "embedding": [0.9, 0.1]})(),
        type("Chunk", (), {"file_id": 1, "content": "b", "embedding": [0.1, 0.9]})(),
    ]
    res = cosine_similarity_search(query=[1.0, 0.0], rows=rows, top_k=1)
    assert len(res) == 1
    assert res[0].content == "a"


def test_ac001_per_file_search_empty():
    assert per_file_top_k_search([1.0, 0.0], [], chunks_per_file=2, max_chunks=12) == []


def test_ac001_search_similar_method_on_repo():
    from einstein_test.vector import VectorRepository

    assert hasattr(VectorRepository, "search_similar")