"""Testes TDD da feature F-005 (endpoints de chat).

Valida AC-002..AC-005 via TestClient contra app FastAPI com SQLite :memory:.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.main import create_app


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    from app.api.dependencies import configure_session_factory

    configure_session_factory(engine)

    app = create_app()
    app.dependency_overrides.clear()
    with TestClient(app) as c:
        yield c
    engine.dispose()


def test_ac002_post_creates_chat(client):
    resp = client.post("/chats", json={"name": "Chat API", "description": "desc"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Chat API"
    assert body["description"] == "desc"
    assert "id" in body


def test_ac002_post_requires_name(client):
    resp = client.post("/chats", json={"description": "sem nome"})
    assert resp.status_code == 422, "name obrigatorio (422 do Pydantic)"


def test_ac003_read_shape(client):
    resp = client.post("/chats", json={"name": "Chat shape"})
    body = resp.json()
    assert set(body.keys()) == {"id", "name", "description"}, (
        "ChatRead expoe id, name, description"
    )
    assert body["description"] is None


def test_ac003_list_returns_chats(client):
    client.post("/chats", json={"name": "A"})
    client.post("/chats", json={"name": "B"})
    resp = client.get("/chats")
    assert resp.status_code == 200
    chats = resp.json()
    assert isinstance(chats, list)
    assert len(chats) == 2


def test_ac003_get_by_id(client):
    created = client.post("/chats", json={"name": "X"}).json()
    resp = client.get(f"/chats/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "X"


def test_ac003_delete_chat(client):
    created = client.post("/chats", json={"name": "D"}).json()
    resp = client.delete(f"/chats/{created['id']}")
    assert resp.status_code == 200
    missing = client.get(f"/chats/{created['id']}")
    assert missing.status_code == 404
    listing = client.get("/chats").json()
    assert all(c["id"] != created["id"] for c in listing), (
        "lista nao retorna chat soft-deletado"
    )


def test_ac005_get_missing_404(client):
    resp = client.get("/chats/999999")
    assert resp.status_code == 404
    assert "detail" in resp.json()


def test_ac005_delete_missing_404(client):
    resp = client.delete("/chats/999999")
    assert resp.status_code == 404
    assert "detail" in resp.json()