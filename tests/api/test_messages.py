"""Testes TDD da feature F-006 (endpoints de messages).

Valida AC-003..AC-005 via TestClient contra app FastAPI com SQLite :memory:.
O POST /chats/{chat_id}/messages agora retorna SSE (F-011): o fixture registra
um RAG fake para não gastar tokens e o id da message é lido do evento [DONE].
"""

import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from einstein_test.db.base import Base
from einstein_test.main import create_app
from einstein_test.services.rag import FakeChatLLM, RagService, reset_rag_factory, set_rag_factory
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

    configure_session_factory(engine)

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
        yield c

    reset_rag_factory()
    engine.dispose()


def _create_chat(client, name="Chat"):
    return client.post("/chats", json={"name": name}).json()


def _post_message(client, chat_id, content, role=None):
    payload = {"content": content}
    if role is not None:
        payload["role"] = role
    resp = client.post(
        f"/chats/{chat_id}/messages",
        json=payload,
        headers={"Accept": "text/event-stream"},
    )
    return resp


def _message_id_from_sse(body: str) -> int:
    m = re.search(r'data:\s*\{"message_id":\s*(\d+)\}', body)
    assert m, f"message_id não encontrado no SSE: {body[:200]}"
    return int(m.group(1))


def test_ac003_create_message_in_chat(client):
    chat = _create_chat(client)
    resp = _post_message(client, chat["id"], "primeira mensagem", role="user")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    body = resp.text
    assert '[DONE]' in body, "SSE conclui"
    msgs = client.get(f"/chats/{chat['id']}/messages").json()
    user = next(m for m in msgs if m["role"] == "user")
    assert user["content"] == "primeira mensagem"
    assert user["chat_id"] == chat["id"]
    assert "id" in user


def test_ac003_create_message_requires_content(client):
    chat = _create_chat(client)
    resp = client.post(f"/chats/{chat['id']}/messages", json={})
    assert resp.status_code == 422, "content obrigatorio"


def test_ac003_list_messages_by_chat(client):
    chat = _create_chat(client)
    _post_message(client, chat["id"], "a")
    _post_message(client, chat["id"], "b")
    resp = client.get(f"/chats/{chat['id']}/messages")
    assert resp.status_code == 200
    msgs = resp.json()
    assert isinstance(msgs, list) and len(msgs) == 4  # 2 user + 2 assistant


def test_ac003_list_messages_isolated_per_chat(client):
    chat_a = _create_chat(client, "A")
    chat_b = _create_chat(client, "B")
    _post_message(client, chat_a["id"], "msg A")
    resp_b = client.get(f"/chats/{chat_b['id']}/messages")
    assert resp_b.json() == []


def test_ac003_get_message_by_id(client):
    chat = _create_chat(client)
    _post_message(client, chat["id"], "busca")
    msgs = client.get(f"/chats/{chat['id']}/messages").json()
    user = next(m for m in msgs if m["role"] == "user")
    got = client.get(f"/messages/{user['id']}")
    assert got.status_code == 200
    assert got.json()["content"] == "busca"


def test_ac003_delete_message(client):
    chat = _create_chat(client)
    resp = _post_message(client, chat["id"], "remove")
    created_id = _message_id_from_sse(resp.text)
    msgs = client.get(f"/chats/{chat['id']}/messages").json()
    user = next(m for m in msgs if m["role"] == "user")
    resp_del = client.delete(f"/messages/{user['id']}")
    assert resp_del.status_code == 200
    assert client.get(f"/messages/{user['id']}").status_code == 404
    listing = client.get(f"/chats/{chat['id']}/messages").json()
    assert all(m["id"] != user["id"] for m in listing), "soft delete na lista"


def test_ac004_message_read_shape(client):
    chat = _create_chat(client)
    _post_message(client, chat["id"], "shape")
    msgs = client.get(f"/chats/{chat['id']}/messages").json()
    body = msgs[0]
    assert "id" in body and "content" in body
    assert "role" in body and "chat_id" in body
    assert "created_at" in body


def test_ac005_missing_chat_404(client):
    resp_post = client.post("/chats/999999/messages", json={"content": "x"})
    assert resp_post.status_code == 404
    resp_list = client.get("/chats/999999/messages")
    assert resp_list.status_code == 404
    assert "detail" in resp_post.json()


def test_ac005_missing_message_404(client):
    resp_get = client.get("/messages/999999")
    assert resp_get.status_code == 404
    resp_del = client.delete("/messages/999999")
    assert resp_del.status_code == 404
    assert "detail" in resp_get.json()


def test_ac005_soft_deleted_chat_404(client):
    chat = _create_chat(client)
    client.delete(f"/chats/{chat['id']}")
    resp_post = client.post(f"/chats/{chat['id']}/messages", json={"content": "x"})
    assert resp_post.status_code == 404, "chat soft-deletado -> 404 no POST"
    resp_list = client.get(f"/chats/{chat['id']}/messages")
    assert resp_list.status_code == 404, "chat soft-deletado -> 404 no GET list"


def test_ac004_role_defaults_user(client):
    chat = _create_chat(client)
    _post_message(client, chat["id"], "sem role")
    msgs = client.get(f"/chats/{chat['id']}/messages").json()
    user = next(m for m in msgs if m["role"] == "user")
    assistant = next(m for m in msgs if m["role"] == "assistant")
    assert user["content"] == "sem role", "user criada com conteúdo da pergunta"
    assert assistant["content"], "assistant salva com resposta"


def test_ac003_content_empty_422(client):
    chat = _create_chat(client)
    resp = client.post(f"/chats/{chat['id']}/messages", json={"content": ""})
    assert resp.status_code == 422, "content vazio -> 422 (min_length)"