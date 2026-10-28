"""Testes TDD da feature F-034 (AC-004/AC-005/AC-006: validações de upload via API).

Valida que os endpoints de upload traduzem as exceções de domínio do service
nos status codes corretos: 422 (vazio), 415 (extensão) e 409 (duplicado) no
single; failures com reason no batch.
"""

import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from einstein_test.db.base import Base
from einstein_test.main import create_app
from einstein_test.storage import InMemoryStorage, set_storage
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
    app = create_app()
    app.dependency_overrides.clear()
    with TestClient(app) as c:
        headers = register_and_login(c, email="val@b.com")
        yield c, headers
    engine.dispose()


def _chat(c, h):
    return c.post("/chats", json={"name": "Chat"}, headers=h).json()


def _upload(c, h, chat_id, name="nota.txt", content=b"conteudo"):
    return c.post(
        f"/chats/{chat_id}/files",
        files={"file": (name, io.BytesIO(content), "text/plain")},
        headers=h,
    )


def _batch(c, h, chat_id, files):
    payload = [
        ("files", (name, io.BytesIO(content), "text/plain"))
        for name, content in files
    ]
    return c.post(f"/chats/{chat_id}/files/batch", files=payload, headers=h)


def body_has_failure(body, reason: str) -> bool:
    return any(f["reason"] == reason for f in body["failures"])


def test_ac004_upload_empty_422(client):
    c, h = client
    chat = _chat(c, h)
    resp = _upload(c, h, chat["id"], content=b"")
    assert resp.status_code == 422, "arquivo vazio -> 422"
    assert "vazio" in resp.json()["detail"].lower()


def test_ac005_upload_unsupported_ext_415(client):
    c, h = client
    chat = _chat(c, h)
    resp = _upload(c, h, chat["id"], name="virus.exe", content=b"MZ")
    assert resp.status_code == 415, "extensão não permitida -> 415"
    assert "suportado" in resp.json()["detail"].lower()


def test_ac006_upload_duplicate_409(client):
    c, h = client
    chat = _chat(c, h)
    first = _upload(c, h, chat["id"], name="nota.txt")
    assert first.status_code == 202
    resp = _upload(c, h, chat["id"], name="NOTA.TXT", content=b"outro")
    assert resp.status_code == 409, "nome duplicado (case-insensitive) -> 409"


def test_ac004_batch_empty_failure(client):
    c, h = client
    chat = _chat(c, h)
    resp = _batch(c, h, chat["id"], [("vazio.txt", b"")])
    assert resp.status_code == 207
    body = resp.json()
    assert body["failures"][0]["reason"] == "arquivo vazio"


def test_ac005_batch_unsupported_failure(client):
    c, h = client
    chat = _chat(c, h)
    resp = _batch(c, h, chat["id"], [("virus.exe", b"MZ")])
    assert resp.status_code == 207
    assert body_has_failure(resp.json(), "tipo de arquivo não suportado")


def test_ac006_batch_duplicate_failure(client):
    c, h = client
    chat = _chat(c, h)
    _upload(c, h, chat["id"], name="nota.txt")
    resp = _batch(c, h, chat["id"], [("NOTA.txt", b"outro")])
    assert resp.status_code == 207
    assert body_has_failure(resp.json(), "arquivo duplicado")
