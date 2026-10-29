"""Testes TDD da feature F-006 (endpoints de messages) — adaptado ao auth (F-012).

Valida AC-003..AC-005 via TestClient contra app FastAPI com SQLite :memory:.
O POST /chats/{chat_id}/messages agora retorna SSE (F-011): o fixture registra
um RAG fake para não gastar tokens.
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
from tests.conftest import register_and_login, seed_ready_file


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
        headers = _register_and_login(c)
        yield c, headers, engine

    reset_rag_factory()
    engine.dispose()


def _register_and_login(client, email="user@b.com"):
    return register_and_login(client, email=email)


def _create_chat(client, headers, name="Chat"):
    return client.post("/chats", json={"name": name}, headers=headers).json()


def _with_ready_file(engine, chat_id):
    seed_ready_file(engine, chat_id)
    return chat_id


def _post_message(client, headers, chat_id, content):
    resp = client.post(
        f"/chats/{chat_id}/messages",
        json={"content": content},
        headers={**headers, "Accept": "text/event-stream"},
    )
    return resp


def _message_id_from_sse(body: str) -> int:
    m = re.search(r'data:\s*\{"message_id":\s*(\d+)\}', body)
    assert m, f"message_id não encontrado no SSE: {body[:200]}"
    return int(m.group(1))


def test_ac003_create_message_in_chat(client):
    c, h, engine = client
    chat = _create_chat(c, h)
    _with_ready_file(engine, chat["id"])
    resp = _post_message(c, h, chat["id"], "primeira mensagem")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    body = resp.text
    assert '[DONE]' in body, "SSE conclui"
    msgs = c.get(f"/chats/{chat['id']}/messages", headers=h).json()["items"]
    user = next(m for m in msgs if m["role"] == "user")
    assert user["content"] == "primeira mensagem"
    assert user["chat_id"] == chat["id"]
    assert "id" in user


def test_ac003_create_message_requires_content(client):
    c, h, engine = client
    chat = _create_chat(c, h)
    resp = c.post(
        f"/chats/{chat['id']}/messages", json={}, headers=h
    )
    assert resp.status_code == 422, "content obrigatorio"


def test_ac003_list_messages_by_chat(client):
    c, h, engine = client
    chat = _create_chat(c, h)
    _with_ready_file(engine, chat["id"])
    _post_message(c, h, chat["id"], "a")
    _post_message(c, h, chat["id"], "b")
    resp = c.get(f"/chats/{chat['id']}/messages", headers=h)
    assert resp.status_code == 200
    msgs = resp.json()["items"]
    assert isinstance(msgs, list) and len(msgs) == 4  # 2 user + 2 assistant


def test_ac003_list_messages_isolated_per_chat(client):
    c, h, engine = client
    chat_a = _create_chat(c, h, "A")
    chat_b = _create_chat(c, h, "B")
    _with_ready_file(engine, chat_a["id"])
    _post_message(c, h, chat_a["id"], "msg A")
    resp_b = c.get(f"/chats/{chat_b['id']}/messages", headers=h)
    assert resp_b.json()["items"] == []


def test_ac003_get_message_by_id(client):
    c, h, engine = client
    chat = _create_chat(c, h)
    _with_ready_file(engine, chat["id"])
    _post_message(c, h, chat["id"], "busca")
    msgs = c.get(f"/chats/{chat['id']}/messages", headers=h).json()["items"]
    user = next(m for m in msgs if m["role"] == "user")
    got = c.get(f"/messages/{user['id']}", headers=h)
    assert got.status_code == 200
    assert got.json()["content"] == "busca"


def test_ac003_delete_message(client):
    c, h, engine = client
    chat = _create_chat(c, h)
    _with_ready_file(engine, chat["id"])
    resp = _post_message(c, h, chat["id"], "remove")
    _message_id_from_sse(resp.text)
    msgs = c.get(f"/chats/{chat['id']}/messages", headers=h).json()["items"]
    user = next(m for m in msgs if m["role"] == "user")
    resp_del = c.delete(f"/messages/{user['id']}", headers=h)
    assert resp_del.status_code == 200
    assert c.get(f"/messages/{user['id']}", headers=h).status_code == 404
    listing = c.get(f"/chats/{chat['id']}/messages", headers=h).json()["items"]
    assert all(m["id"] != user["id"] for m in listing), "soft delete na lista"


def test_ac004_message_read_shape(client):
    c, h, engine = client
    chat = _create_chat(c, h)
    _with_ready_file(engine, chat["id"])
    _post_message(c, h, chat["id"], "shape")
    msgs = c.get(f"/chats/{chat['id']}/messages", headers=h).json()["items"]
    body = msgs[0]
    assert "id" in body and "content" in body
    assert "role" in body and "chat_id" in body
    assert "created_at" in body


def test_ac005_missing_chat_404(client):
    c, h, engine = client
    resp_post = c.post(
        "/chats/999999/messages",
        json={"content": "x"},
        headers={**h, "Accept": "text/event-stream"},
    )
    assert resp_post.status_code == 404
    resp_list = c.get("/chats/999999/messages", headers=h)
    assert resp_list.status_code == 404
    assert "detail" in resp_post.json()


def test_ac005_missing_message_404(client):
    c, h, engine = client
    resp_get = c.get("/messages/999999", headers=h)
    assert resp_get.status_code == 404
    resp_del = c.delete("/messages/999999", headers=h)
    assert resp_del.status_code == 404
    assert "detail" in resp_get.json()


def test_ac005_soft_deleted_chat_404(client):
    c, h, engine = client
    chat = _create_chat(c, h)
    c.delete(f"/chats/{chat['id']}", headers=h)
    resp_post = c.post(
        f"/chats/{chat['id']}/messages",
        json={"content": "x"},
        headers={**h, "Accept": "text/event-stream"},
    )
    assert resp_post.status_code == 404, "chat soft-deletado -> 404 no POST"
    resp_list = c.get(f"/chats/{chat['id']}/messages", headers=h)
    assert resp_list.status_code == 404, "chat soft-deletado -> 404 no GET list"


def test_ac004_role_defaults_user(client):
    c, h, engine = client
    chat = _create_chat(c, h)
    _with_ready_file(engine, chat["id"])
    _post_message(c, h, chat["id"], "sem role")
    msgs = c.get(f"/chats/{chat['id']}/messages", headers=h).json()["items"]
    user = next(m for m in msgs if m["role"] == "user")
    assistant = next(m for m in msgs if m["role"] == "assistant")
    assert user["content"] == "sem role", "user criada com conteúdo da pergunta"
    assert assistant["content"], "assistant salva com resposta"


def test_ac003_content_empty_422(client):
    c, h, engine = client
    chat = _create_chat(c, h)
    resp = c.post(
        f"/chats/{chat['id']}/messages", json={"content": ""}, headers=h
    )
    assert resp.status_code == 422, "content vazio -> 422 (min_length)"