"""Testes TDD da feature F-007 (endpoints de files) — adaptado ao auth (F-012).

Valida AC-004/AC-005 via TestClient com SQLite :memory: + storage fake.
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
        headers = _register_and_login(c)
        yield c, headers
    engine.dispose()


def _register_and_login(client, email="user@b.com"):
    return register_and_login(client, email=email)


def _create_chat(client, headers, name="Chat"):
    return client.post("/chats", json={"name": name}, headers=headers).json()


def _upload(client, headers, chat_id, name="doc.pdf", content=b"%PDF", type_="application/pdf"):
    return client.post(
        f"/chats/{chat_id}/files",
        files={"file": (name, io.BytesIO(content), type_)},
        headers=headers,
    )


def test_ac004_upload_file_to_chat(client):
    c, h = client
    chat = _create_chat(c, h)
    resp = _upload(c, h, chat["id"])
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "doc.pdf"
    assert body["size"] == 4
    assert body["chat_id"] == chat["id"]
    assert body["url"]


def test_ac004_list_files_by_chat(client):
    c, h = client
    chat = _create_chat(c, h)
    _upload(c, h, chat["id"], name="a.txt", content=b"a")
    _upload(c, h, chat["id"], name="b.txt", content=b"bb")
    resp = c.get(f"/chats/{chat['id']}/files", headers=h)
    assert resp.status_code == 200
    files = resp.json()
    assert isinstance(files, list) and len(files) == 2


def test_ac004_list_files_isolated_per_chat(client):
    c, h = client
    chat_a = _create_chat(c, h, "A")
    chat_b = _create_chat(c, h, "B")
    _upload(c, h, chat_a["id"], name="x.txt", content=b"x")
    assert c.get(f"/chats/{chat_b['id']}/files", headers=h).json() == []


def test_ac004_get_file_by_id(client):
    c, h = client
    chat = _create_chat(c, h)
    created = _upload(c, h, chat["id"], name="busca.bin", content=b"data").json()
    resp = c.get(f"/files/{created['id']}", headers=h)
    assert resp.status_code == 200
    assert resp.json()["name"] == "busca.bin"


def test_ac004_delete_file(client):
    c, h = client
    chat = _create_chat(c, h)
    created = _upload(c, h, chat["id"], name="remove.bin", content=b"r").json()
    resp = c.delete(f"/files/{created['id']}", headers=h)
    assert resp.status_code == 200
    assert c.get(f"/files/{created['id']}", headers=h).status_code == 404
    listing = c.get(f"/chats/{chat['id']}/files", headers=h).json()
    assert all(f["id"] != created["id"] for f in listing)


def test_ac004_read_shape(client):
    c, h = client
    chat = _create_chat(c, h)
    body = _upload(c, h, chat["id"], name="shape.bin", content=b"s").json()
    assert {"id", "name", "url", "type", "size", "chat_id", "created_at"} <= set(body)


def test_ac005_missing_chat_404(client):
    c, h = client
    resp_upload = _upload(c, h, 999999)
    assert resp_upload.status_code == 404
    resp_list = c.get("/chats/999999/files", headers=h)
    assert resp_list.status_code == 404
    assert "detail" in resp_upload.json()


def test_ac005_missing_file_404(client):
    c, h = client
    resp_get = c.get("/files/999999", headers=h)
    assert resp_get.status_code == 404
    resp_del = c.delete("/files/999999", headers=h)
    assert resp_del.status_code == 404
    assert "detail" in resp_get.json()


def test_ac005_soft_deleted_chat_404(client):
    c, h = client
    chat = _create_chat(c, h)
    c.delete(f"/chats/{chat['id']}", headers=h)
    assert _upload(c, h, chat["id"]).status_code == 404
    assert c.get(f"/chats/{chat['id']}/files", headers=h).status_code == 404


def test_ac004_upload_sanitizes_traversal_name(client):
    from einstein_test.storage import get_storage

    c, h = client
    chat = _create_chat(c, h)
    resp = _upload(c, h, chat["id"], name="../../etc/passwd", content=b"x")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "passwd", "nome sanitizado (basename)"
    storage = get_storage()
    assert not any(".." in k for k in storage._objects), "sem traversal na chave"


def test_ac004_upload_over_limit_413(client):
    c, h = client
    chat = _create_chat(c, h)
    big = b"0" * (51 * 1024 * 1024)
    resp = _upload(c, h, chat["id"], name="big.bin", content=big)
    assert resp.status_code == 413, "upload acima do limite -> 413"


def test_ac004_delete_removes_object(client):
    from einstein_test.storage import get_storage

    c, h = client
    chat = _create_chat(c, h)
    created = _upload(c, h, chat["id"], name="limpar.txt", content=b"d").json()
    storage = get_storage()
    key = created["url"].split("/", 3)[3]
    assert key in storage._objects
    c.delete(f"/files/{created['id']}", headers=h)
    assert key not in storage._objects, "objeto removido do storage no delete"


def test_ac004_content_type_sent(client):
    c, h = client
    chat = _create_chat(c, h)
    body = _upload(c, h, chat["id"], name="doc.pdf", content=b"%PDF").json()
    assert body["type"] == "application/pdf"