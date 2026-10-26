"""Testes TDD da feature F-007 (endpoints de files).

Valida AC-004/AC-005 via TestClient com SQLite :memory: + storage fake.
"""

import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.main import create_app
from app.storage import InMemoryStorage


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    from app.api.dependencies import configure_session_factory
    from app.storage import set_storage

    configure_session_factory(engine)
    set_storage(InMemoryStorage())

    app = create_app()
    app.dependency_overrides.clear()
    with TestClient(app) as c:
        yield c
    engine.dispose()


def _create_chat(client, name="Chat"):
    return client.post("/chats", json={"name": name}).json()


def _upload(client, chat_id, name="doc.pdf", content=b"%PDF", type_="application/pdf"):
    return client.post(
        f"/chats/{chat_id}/files",
        files={"file": (name, io.BytesIO(content), type_)},
    )


def test_ac004_upload_file_to_chat(client):
    chat = _create_chat(client)
    resp = _upload(client, chat["id"])
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "doc.pdf"
    assert body["size"] == 4
    assert body["chat_id"] == chat["id"]
    assert body["url"]


def test_ac004_list_files_by_chat(client):
    chat = _create_chat(client)
    _upload(client, chat["id"], name="a.txt", content=b"a")
    _upload(client, chat["id"], name="b.txt", content=b"bb")
    resp = client.get(f"/chats/{chat['id']}/files")
    assert resp.status_code == 200
    files = resp.json()
    assert isinstance(files, list) and len(files) == 2


def test_ac004_list_files_isolated_per_chat(client):
    chat_a = _create_chat(client, "A")
    chat_b = _create_chat(client, "B")
    _upload(client, chat_a["id"], name="x.txt", content=b"x")
    assert client.get(f"/chats/{chat_b['id']}/files").json() == []


def test_ac004_get_file_by_id(client):
    chat = _create_chat(client)
    created = _upload(client, chat["id"], name="busca.bin", content=b"data").json()
    resp = client.get(f"/files/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "busca.bin"


def test_ac004_delete_file(client):
    chat = _create_chat(client)
    created = _upload(client, chat["id"], name="remove.bin", content=b"r").json()
    resp = client.delete(f"/files/{created['id']}")
    assert resp.status_code == 200
    assert client.get(f"/files/{created['id']}").status_code == 404
    listing = client.get(f"/chats/{chat['id']}/files").json()
    assert all(f["id"] != created["id"] for f in listing)


def test_ac004_read_shape(client):
    chat = _create_chat(client)
    body = _upload(client, chat["id"], name="shape.bin", content=b"s").json()
    assert {"id", "name", "url", "type", "size", "chat_id", "created_at"} <= set(body)


def test_ac005_missing_chat_404(client):
    resp_upload = _upload(client, 999999)
    assert resp_upload.status_code == 404
    resp_list = client.get("/chats/999999/files")
    assert resp_list.status_code == 404
    assert "detail" in resp_upload.json()


def test_ac005_missing_file_404(client):
    resp_get = client.get("/files/999999")
    assert resp_get.status_code == 404
    resp_del = client.delete("/files/999999")
    assert resp_del.status_code == 404
    assert "detail" in resp_get.json()


def test_ac005_soft_deleted_chat_404(client):
    chat = _create_chat(client)
    client.delete(f"/chats/{chat['id']}")
    assert _upload(client, chat["id"]).status_code == 404
    assert client.get(f"/chats/{chat['id']}/files").status_code == 404


def test_ac004_upload_sanitizes_traversal_name(client):
    from app.storage import get_storage

    chat = _create_chat(client)
    resp = _upload(client, chat["id"], name="../../etc/passwd", content=b"x")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "passwd", "nome sanitizado (basename)"
    storage = get_storage()
    assert not any(".." in k for k in storage._objects), "sem traversal na chave"


def test_ac004_upload_over_limit_413(client):
    chat = _create_chat(client)
    big = b"0" * (51 * 1024 * 1024)
    resp = _upload(client, chat["id"], name="big.bin", content=big)
    assert resp.status_code == 413, "upload acima do limite -> 413"


def test_ac004_delete_removes_object(client):
    from app.storage import get_storage

    chat = _create_chat(client)
    created = _upload(client, chat["id"], name="limpar.txt", content=b"d").json()
    storage = get_storage()
    key = created["url"].split("/", 3)[3]
    assert key in storage._objects
    client.delete(f"/files/{created['id']}")
    assert key not in storage._objects, "objeto removido do storage no delete"


def test_ac004_content_type_sent(client):
    chat = _create_chat(client)
    body = _upload(client, chat["id"], name="doc.pdf", content=b"%PDF").json()
    assert body["type"] == "application/pdf"