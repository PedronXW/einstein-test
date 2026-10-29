"""Testes TDD da feature F-030 (upload múltiplo de arquivos em uma única chamada).

Valida AC-001/AC-006 via TestClient com SQLite :memory: + storage fake.
"""

import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from einstein_test.db.base import Base
from einstein_test.main import create_app
from einstein_test.storage import InMemoryStorage
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
    from einstein_test.storage import set_storage

    configure_session_factory(engine)
    set_storage(InMemoryStorage())

    app = create_app()
    app.dependency_overrides.clear()
    with TestClient(app) as c:
        headers = register_and_login(c, email="batch@b.com")
        yield c, headers
    engine.dispose()


def _create_chat(client, headers, name="Chat"):
    return client.post("/chats", json={"name": name}, headers=headers).json()


def _batch_upload(client, headers, chat_id, files):
    payload = [
        ("files", (name, io.BytesIO(content), type_))
        for name, content, type_ in files
    ]
    return client.post(
        f"/chats/{chat_id}/files/batch", files=payload, headers=headers
    )


def test_ac001_batch_upload_multiple_files(client):
    c, h = client
    chat = _create_chat(c, h)
    resp = _batch_upload(c, h, chat["id"], [
        ("a.txt", b"aaa", "text/plain"),
        ("b.pdf", b"%PDF", "application/pdf"),
    ])
    assert resp.status_code == 207, "lote processado com sucesso parcial"
    body = resp.json()
    assert len(body["created"]) == 2
    assert body["failures"] == []


def test_ac001_single_file_endpoint_still_works(client):
    c, h = client
    chat = _create_chat(c, h)
    resp = c.post(
        f"/chats/{chat['id']}/files",
        files={"file": ("unico.txt", io.BytesIO(b"u"), "text/plain")},
        headers=h,
    )
    assert resp.status_code == 202
    assert resp.json()["name"] == "unico.txt"


def test_ac002_all_valid_returns_file_read_fields(client, enqueue_spy):
    c, h = client
    chat = _create_chat(c, h)
    resp = _batch_upload(c, h, chat["id"], [
        ("a.txt", b"aaa", "text/plain"),
        ("b.pdf", b"%PDF", "application/pdf"),
    ])
    assert resp.status_code == 207
    body = resp.json()
    assert len(body["created"]) == 2
    assert body["failures"] == []
    created = body["created"]
    for f in created:
        assert {"id", "chat_id", "name", "url", "type", "size", "created_at", "status"} <= set(f)
        assert f["chat_id"] == chat["id"]
        assert f["status"] == "pending"
    assert sorted(f["name"] for f in created) == ["a.txt", "b.pdf"]
    assert [f["id"] for f in created] == enqueue_spy, "vetorização enfileirada por arquivo"


def test_ac003_partial_failure_keeps_valid_and_reports(client, monkeypatch):
    import einstein_test.services.file as file_service

    c, h = client
    chat = _create_chat(c, h)
    monkeypatch.setattr(file_service, "MAX_UPLOAD_SIZE", 4)
    resp = _batch_upload(c, h, chat["id"], [
        ("ok.txt", b"abc", "text/plain"),
        ("big.txt", b"x" * 100, "text/plain"),
    ])
    assert resp.status_code == 207
    body = resp.json()
    assert [f["name"] for f in body["created"]] == ["ok.txt"]
    assert len(body["failures"]) == 1
    failure = body["failures"][0]
    assert failure["index"] == 1
    assert failure["name"] == "big.txt"
    assert failure["reason"] == "arquivo muito grande"
    listing = c.get(f"/chats/{chat['id']}/files", headers=h).json()["items"]
    assert [f["name"] for f in listing] == ["ok.txt"], "válido persistido mesmo com inválido"


def test_ac004_over_limit_goes_to_failures_only(client, monkeypatch, enqueue_spy):
    import einstein_test.services.file as file_service

    c, h = client
    chat = _create_chat(c, h)
    monkeypatch.setattr(file_service, "MAX_UPLOAD_SIZE", 4)
    resp = _batch_upload(c, h, chat["id"], [
        ("big.txt", b"x" * 100, "text/plain"),
        ("ok.txt", b"abc", "text/plain"),
    ])
    assert resp.status_code == 207
    body = resp.json()
    assert [f["name"] for f in body["created"]] == ["ok.txt"]
    assert len(body["failures"]) == 1
    assert body["failures"][0]["name"] == "big.txt"
    assert body["failures"][0]["reason"] == "arquivo muito grande"
    listing = c.get(f"/chats/{chat['id']}/files", headers=h).json()["items"]
    assert len(listing) == 1
    assert [f["id"] for f in body["created"]] == enqueue_spy, "inválido não enfileirado"


def test_ac005_max_files_boundary_207(client):
    c, h = client
    chat = _create_chat(c, h)
    exactly_20 = [(f"f{i}.txt", b"x", "text/plain") for i in range(20)]
    resp = _batch_upload(c, h, chat["id"], exactly_20)
    assert resp.status_code == 207, "limite exato (20) aceito"
    assert len(resp.json()["created"]) == 20
    assert resp.json()["failures"] == []


def test_ac005_more_than_max_files_413(client):
    c, h = client
    chat = _create_chat(c, h)
    many = [(f"f{i}.txt", b"x", "text/plain") for i in range(21)]
    resp = _batch_upload(c, h, chat["id"], many)
    assert resp.status_code == 413, "lote acima de MAX_FILES -> 413"
    assert "detail" in resp.json()


def test_ac006_missing_chat_404(client):
    c, h = client
    resp = _batch_upload(c, h, 999999, [("a.txt", b"x", "text/plain")])
    assert resp.status_code == 404
    assert "detail" in resp.json()
