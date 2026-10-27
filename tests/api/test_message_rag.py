"""Testes TDD da feature F-011 (AC-004/AC-005/AC-007: streaming SSE no POST /messages).

Valida que POST /chats/{chat_id}/messages agora retorna text/event-stream com
os tokens do LLM fake, [DONE] com o message_id da resposta salva como
role=assistant, e error sem salvar em falha do LLM.
"""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from einstein_test.db.base import Base
from einstein_test.main import create_app
from einstein_test.services.rag import FakeChatLLM, RagService, set_rag_factory


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    from einstein_test.api.dependencies import configure_session_factory

    configure_session_factory(engine)

    from einstein_test.services.rag import RagService, set_rag_factory
    from einstein_test.vector import FakeEmbedder

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
        yield c, engine

    from einstein_test.services.rag import reset_rag_factory

    reset_rag_factory()
    engine.dispose()


def _create_chat(client):
    return client.post("/chats", json={"name": "Chat"}).json()


def _ask(client, chat_id, content="pergunta"):
    return client.post(
        f"/chats/{chat_id}/messages",
        json={"content": content},
        headers={"Accept": "text/event-stream"},
    )


def test_ac004_post_messages_returns_sse(client):
    c, engine = client
    chat = _create_chat(c)
    resp = _ask(c, chat["id"])
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")


def test_ac004_sse_contains_tokens_and_done(client):
    c, engine = client
    chat = _create_chat(c)
    resp = _ask(c, chat["id"], content="pergunta")
    body = resp.text
    assert '"token1"' in body, "tokens do LLM fake no SSE"
    assert '"token2"' in body
    assert "[DONE]" in body, "evento [DONE] presente"
    assert "message_id" in body, "id da resposta no stream"
    # [DONE] é o último evento
    last_frame = body.rstrip().split("\n\n")[-1]
    assert "DONE" in last_frame, "[DONE] deve ser o último evento"


def test_ac004_assistant_message_persisted(client):
    c, engine = client
    chat = _create_chat(c)
    resp = _ask(c, chat["id"])
    assert resp.status_code == 200
    msgs = c.get(f"/chats/{chat['id']}/messages").json()
    roles = [m["role"] for m in msgs]
    assert "user" in roles, "message user criada"
    assert "assistant" in roles, "message assistant salva"
    assistant = next(m for m in msgs if m["role"] == "assistant")
    assert assistant["content"] == "token1token2", "resposta = tokens concatenados"


def test_ac005_llm_error_emits_error_event_without_saving(client):
    c, engine = client
    chat = _create_chat(c)

    from einstein_test.services.rag import reset_rag_factory
    from einstein_test.vector import FakeEmbedder

    class _BoomLLM:
        def stream(self, prompt):
            raise RuntimeError("llm quebrou")
            yield "nunca"

    def _factory(*args, **kwargs):
        return RagService(
            llm=_BoomLLM(),
            retriever=kwargs["retriever"],
            embedder=FakeEmbedder(),
        )

    set_rag_factory(_factory)
    try:
        resp = _ask(c, chat["id"], content="quebra?")
        assert "error" in resp.text.lower(), "evento de erro presente"
        msgs = c.get(f"/chats/{chat['id']}/messages").json()
        roles = [m["role"] for m in msgs]
        assert "assistant" not in roles, "nenhuma assistant salva em erro"
        assert "user" in roles, "message user permanece"
    finally:
        reset_rag_factory()


def test_ac007_missing_chat_404(client):
    c, engine = client
    resp = _ask(c, 999999)
    assert resp.status_code == 404