"""Testes TDD da feature F-006 (endpoints de messages).

Valida AC-003..AC-005 via TestClient contra app FastAPI com SQLite :memory:.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from einstein_test.db.base import Base
from einstein_test.main import create_app


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

    app = create_app()
    app.dependency_overrides.clear()
    with TestClient(app) as c:
        yield c
    engine.dispose()


def _create_chat(client, name="Chat"):
    return client.post("/chats", json={"name": name}).json()


def test_ac003_create_message_in_chat(client):
    chat = _create_chat(client)
    resp = client.post(
        f"/chats/{chat['id']}/messages",
        json={"content": "primeira mensagem", "role": "user"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["content"] == "primeira mensagem"
    assert body["role"] == "user"
    assert body["chat_id"] == chat["id"]
    assert "id" in body


def test_ac003_create_message_requires_content(client):
    chat = _create_chat(client)
    resp = client.post(f"/chats/{chat['id']}/messages", json={})
    assert resp.status_code == 422, "content obrigatorio"


def test_ac003_list_messages_by_chat(client):
    chat = _create_chat(client)
    client.post(f"/chats/{chat['id']}/messages", json={"content": "a"})
    client.post(f"/chats/{chat['id']}/messages", json={"content": "b"})
    resp = client.get(f"/chats/{chat['id']}/messages")
    assert resp.status_code == 200
    msgs = resp.json()
    assert isinstance(msgs, list) and len(msgs) == 2


def test_ac003_list_messages_isolated_per_chat(client):
    chat_a = _create_chat(client, "A")
    chat_b = _create_chat(client, "B")
    client.post(f"/chats/{chat_a['id']}/messages", json={"content": "msg A"})
    resp_b = client.get(f"/chats/{chat_b['id']}/messages")
    assert resp_b.json() == []


def test_ac003_get_message_by_id(client):
    chat = _create_chat(client)
    created = client.post(
        f"/chats/{chat['id']}/messages", json={"content": "busca"}
    ).json()
    resp = client.get(f"/messages/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["content"] == "busca"


def test_ac003_delete_message(client):
    chat = _create_chat(client)
    created = client.post(
        f"/chats/{chat['id']}/messages", json={"content": "remove"}
    ).json()
    resp = client.delete(f"/messages/{created['id']}")
    assert resp.status_code == 200
    assert client.get(f"/messages/{created['id']}").status_code == 404
    listing = client.get(f"/chats/{chat['id']}/messages").json()
    assert all(m["id"] != created["id"] for m in listing), "soft delete na lista"


def test_ac004_message_read_shape(client):
    chat = _create_chat(client)
    body = client.post(
        f"/chats/{chat['id']}/messages", json={"content": "shape"}
    ).json()
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


def test_ac004_role_defaults_none(client):
    chat = _create_chat(client)
    body = client.post(
        f"/chats/{chat['id']}/messages", json={"content": "sem role"}
    ).json()
    assert body["role"] is None, "role default None no MessageRead"


def test_ac003_content_empty_422(client):
    chat = _create_chat(client)
    resp = client.post(f"/chats/{chat['id']}/messages", json={"content": ""})
    assert resp.status_code == 422, "content vazio -> 422 (min_length)"