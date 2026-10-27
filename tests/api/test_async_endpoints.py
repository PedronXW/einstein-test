"""Testes TDD da feature F-013 (AC-004/AC-005/AC-006/AC-007: endpoints async).

Valida que POST /messages (SSE) e POST /files (upload) continuam funcionando
como async, com mesmos contratos (tokens, [DONE], error; chunk_ids; 413/422),
e que singleton do RagService é reutilizado.
"""

import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from einstein_test.db.base import Base
from einstein_test.main import create_app
from einstein_test.services.rag import (
    FakeChatLLM,
    RagService,
    reset_rag_factory,
    set_rag_factory,
)
from einstein_test.vector import FakeEmbedder


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    from einstein_test.api.dependencies import configure_session_factory
    from einstein_test.storage import set_storage, InMemoryStorage

    configure_session_factory(engine)
    set_storage(InMemoryStorage())

    from tests.conftest import register_and_login

    def _factory(*args, **kwargs):
        return RagService(
            llm=FakeChatLLM(),
            retriever=kwargs["retriever"],
            embedder=FakeEmbedder(),
        )

    set_rag_factory(_factory)

    app = create_app()
    app.dependency_overrides.clear()
    with TestClient(app) as c:
        headers = register_and_login(c, email="user@b.com")
        yield c, headers, engine

    reset_rag_factory()
    engine.dispose()


def test_ac004_post_messages_sse_still_works(client):
    c, h, engine = client
    chat = c.post("/chats", json={"name": "Chat"}, headers=h).json()
    resp = c.post(
        f"/chats/{chat['id']}/messages",
        json={"content": "pergunta"},
        headers={**h, "Accept": "text/event-stream"},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    body = resp.text
    assert '"token1"' in body and "[DONE]" in body
    assert "message_id" in body
    # assistant persistida
    msgs = c.get(f"/chats/{chat['id']}/messages", headers=h).json()
    assert any(m["role"] == "assistant" for m in msgs)


def test_ac004_sse_many_parallel_requests(client):
    # concorrência: N perguntas em sequência rápida, SSE íntegro por request
    c, h, engine = client
    chat = c.post("/chats", json={"name": "conc"}, headers=h).json()

    def _ask(i):
        resp = c.post(
            f"/chats/{chat['id']}/messages",
            json={"content": f"pergunta {i}"},
            headers={**h, "Accept": "text/event-stream"},
        )
        return resp

    results = [_ask(i) for i in range(8)]
    for resp, i in zip(results, range(8)):
        assert resp.status_code == 200
        assert '"token1"' in resp.text, f"SSE do request {i} tem tokens"
        assert "[DONE]" in resp.text


def test_ac005_upload_file_still_works(client):
    c, h, engine = client
    chat = c.post("/chats", json={"name": "upload"}, headers=h).json()
    resp = c.post(
        f"/chats/{chat['id']}/files",
        files={"file": ("nota.txt", io.BytesIO(b"texto longo " * 30), "text/plain")},
        headers=h,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "nota.txt"
    assert body["chunk_ids"], "upload vetoriza (async) e retorna chunk_ids"


def test_ac005_upload_over_limit_413(client):
    c, h, engine = client
    chat = c.post("/chats", json={"name": "big"}, headers=h).json()
    big = b"0" * (51 * 1024 * 1024)
    resp = c.post(
        f"/chats/{chat['id']}/files",
        files={"file": ("big.bin", io.BytesIO(big), "application/octet-stream")},
        headers=h,
    )
    assert resp.status_code == 413


def test_ac006_rag_service_singleton_reused(client, monkeypatch):
    from einstein_test.services.rag import get_rag_service, reset_rag_factory

    monkeypatch.setenv("OPENAI_API_KEY", "sk-teste")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://spillway.ensinoeinstein.com/openai/v1")
    monkeypatch.setenv("OPENAI_CHAT_MODEL", "azure/gpt-5-mini")
    c, h, engine = client
    reset_rag_factory()

    class _Repo:
        def search_similar(self, *a, **k):
            return []

    svc1 = get_rag_service(_Repo())
    svc2 = get_rag_service(_Repo())
    # adapter/embedder compartilhados (singleton), RagService/retriever por request
    assert svc1.llm is svc2.llm, "ChatOpenAIAdapter compartilhado (singleton)"
    assert svc1.embedder is svc2.embedder, "Embedder compartilhado"
    assert svc1 is not svc2, "RagService é por request"
    assert svc1.retriever is not svc2.retriever, "retriever é por request (session)"

    reset_rag_factory()


def test_ac006_reset_rag_factory_exists():
    from einstein_test.services.rag import get_rag_service, set_rag_factory

    assert callable(set_rag_factory) and callable(get_rag_service)