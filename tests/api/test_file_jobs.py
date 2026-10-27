"""Testes TDD da feature F-015 (AC-002/AC-003/AC-007: upload 202 + status via API).

Valida que POST /files retorna 202 com status=pending e enfileira (mock da
task), GET /files/{id} expõe status, e ownership preservado.
"""

import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from einstein_test.db.base import Base
from einstein_test.main import create_app
from einstein_test.storage import set_storage, InMemoryStorage
from einstein_test.vector import FakeEmbedder, set_embedder
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
    set_storage(InMemoryStorage())
    set_embedder(FakeEmbedder())

    app = create_app()
    app.dependency_overrides.clear()
    with TestClient(app) as c:
        headers = register_and_login(c, email="user@b.com")
        yield c, headers
    engine.dispose()


def _upload(client, headers, chat_id, name="nota.txt", content=b"texto longo " * 5):
    return client.post(
        f"/chats/{chat_id}/files",
        files={"file": (name, io.BytesIO(content), "text/plain")},
        headers=headers,
    )


def test_ac002_upload_returns_202_pending(client, enqueue_spy):
    c, h = client
    chat = c.post("/chats", json={"name": "Chat"}, headers=h).json()
    resp = _upload(c, h, chat["id"])
    assert resp.status_code == 202, "upload aceito (processamento em background)"
    body = resp.json()
    assert body["status"] == "pending", "status pending no upload"
    assert body["id"], "File id presente"
    assert len(enqueue_spy) == 1, "task enfileirada"
    assert enqueue_spy[0] == body["id"]


def test_ac002_upload_read_shape_includes_status(client):
    c, h = client
    chat = c.post("/chats", json={"name": "Chat"}, headers=h).json()
    body = _upload(c, h, chat["id"]).json()
    assert {"status", "error_detail", "chunk_ids", "vector_reference"} <= set(body)


def test_ac003_get_file_reflects_status(client):
    c, h = client
    chat = c.post("/chats", json={"name": "Chat"}, headers=h).json()
    created = _upload(c, h, chat["id"]).json()

    # simula o worker: marca o file como ready (usa o engine já configurado)
    from sqlalchemy.orm import Session
    from sqlalchemy import create_engine as _ce
    from einstein_test.api.dependencies import _SessionLocal
    from einstein_test.models.file import File

    assert _SessionLocal is not None
    with _SessionLocal() as s:
        f = s.get(File, created["id"])
        f.status = "ready"
        f.chunk_ids = [1, 2]
        f.vector_reference = "vec-123"
        s.commit()

    got = c.get(f"/files/{created['id']}", headers=h).json()
    assert got["status"] == "ready", "GET reflete status do worker"
    assert got["chunk_ids"] == [1, 2]
    assert got["error_detail"] is None


def test_ac007_upload_over_limit_413(client):
    c, h = client
    chat = c.post("/chats", json={"name": "Chat"}, headers=h).json()
    big = b"0" * (51 * 1024 * 1024)
    resp = _upload(c, h, chat["id"], content=big)
    assert resp.status_code == 413


def test_ac007_ownership_preserved(client):
    c, h = client
    from tests.conftest import register_and_login

    h2 = register_and_login(c, email="outro@b.com")
    chat_a = c.post("/chats", json={"name": "A"}, headers=h).json()
    created = _upload(c, h, chat_a["id"]).json()
    assert c.get(f"/files/{created['id']}", headers=h2).status_code == 404, (
        "usuário B não vê file do chat de A"
    )