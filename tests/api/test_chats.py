"""Testes TDD da feature F-005 (endpoints de chat) — adaptado ao auth (F-012).

Valida AC-002..AC-005 via TestClient com usuário autenticado.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from einstein_test.db.base import Base
from einstein_test.main import create_app
from tests.conftest import register_and_login


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


def _register_and_login(client, email="user@b.com"):
    return register_and_login(client, email=email)


def _create_chat(client, headers, name="Chat API", description=None):
    return client.post(
        "/chats", json={"name": name, "description": description}, headers=headers
    )


def test_ac002_post_creates_chat(client):
    h = _register_and_login(client)
    resp = _create_chat(client, h, name="Chat API", description="desc")
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Chat API"
    assert body["description"] == "desc"
    assert "id" in body


def test_ac002_post_requires_name(client):
    h = _register_and_login(client)
    resp = client.post("/chats", json={"description": "sem nome"}, headers=h)
    assert resp.status_code == 422, "name obrigatorio (422 do Pydantic)"


def test_ac003_read_shape(client):
    h = _register_and_login(client)
    resp = _create_chat(client, h, name="Chat shape")
    body = resp.json()
    assert set(body.keys()) == {"id", "name", "description"}, (
        "ChatRead expoe id, name, description"
    )
    assert body["description"] is None


def test_ac003_list_returns_chats(client):
    h = _register_and_login(client)
    _create_chat(client, h, name="A")
    _create_chat(client, h, name="B")
    resp = client.get("/chats", headers=h)
    assert resp.status_code == 200
    chats = resp.json()["items"]
    assert isinstance(chats, list)
    assert len(chats) == 2


def test_ac003_get_by_id(client):
    h = _register_and_login(client)
    created = _create_chat(client, h, name="X").json()
    resp = client.get(f"/chats/{created['id']}", headers=h)
    assert resp.status_code == 200
    assert resp.json()["name"] == "X"


def test_ac003_delete_chat(client):
    h = _register_and_login(client)
    created = _create_chat(client, h, name="D").json()
    resp = client.delete(f"/chats/{created['id']}", headers=h)
    assert resp.status_code == 200
    missing = client.get(f"/chats/{created['id']}", headers=h)
    assert missing.status_code == 404
    listing = client.get("/chats", headers=h).json()["items"]
    assert all(c["id"] != created["id"] for c in listing), (
        "lista nao retorna chat soft-deletado"
    )


def test_ac005_get_missing_404(client):
    h = _register_and_login(client)
    resp = client.get("/chats/999999", headers=h)
    assert resp.status_code == 404
    assert "detail" in resp.json()


def test_ac005_delete_missing_404(client):
    h = _register_and_login(client)
    resp = client.delete("/chats/999999", headers=h)
    assert resp.status_code == 404
    assert "detail" in resp.json()