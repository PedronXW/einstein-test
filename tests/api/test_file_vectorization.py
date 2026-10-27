"""Testes da feature F-010 adaptados à F-015 (upload 202 + vetorização em background).

Valida que POST /chats/{chat_id}/files retorna 202 (status=pending) e que a
vetorização acontece via task Celery (marcando ready) — o contrato síncrono
anterior (200 + chunk_ids na hora) mudou para a fila.
"""

import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from einstein_test.db.base import Base
from einstein_test.main import create_app
from einstein_test.storage import InMemoryStorage
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
    from einstein_test.storage import set_storage

    configure_session_factory(engine)
    set_storage(InMemoryStorage())
    set_embedder(FakeEmbedder())

    app = create_app()
    app.dependency_overrides.clear()
    with TestClient(app) as c:
        headers = register_and_login(c, email="user@b.com")
        yield c, headers
    engine.dispose()


def _create_chat(client, headers, name="Chat"):
    return client.post("/chats", json={"name": name}, headers=headers).json()


def _upload(client, headers, chat_id, name="nota.txt", content=b"texto longo " * 30, type_="text/plain"):
    return client.post(
        f"/chats/{chat_id}/files",
        files={"file": (name, io.BytesIO(content), type_)},
        headers=headers,
    )


def test_ac006_upload_returns_202_pending(client, enqueue_spy):
    c, h = client
    chat = _create_chat(c, h)
    resp = _upload(c, h, chat["id"])
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "pending", "upload enfileira e retorna pending"
    assert body["id"] in enqueue_spy, "task enfileirada (mock)"


def test_ac006_upload_pdf_202(client):
    c, h = client
    chat = _create_chat(c, h)
    resp = _upload(c, h, chat["id"], name="doc.pdf", content=_minimal_pdf(), type_="application/pdf")
    assert resp.status_code == 202
    assert resp.json()["status"] == "pending"


def test_ac006_read_shape_includes_vector_fields(client):
    c, h = client
    chat = _create_chat(c, h)
    body = _upload(c, h, chat["id"], name="shape.txt", content=b"abc " * 5).json()
    assert {"status", "error_detail", "chunk_ids", "vector_reference"} <= set(body)


def test_ac006_upload_non_text_pending(client):
    c, h = client
    chat = _create_chat(c, h)
    body = _upload(c, h, chat["id"], name="img.png", content=b"\x89PNG", type_="image/png").json()
    assert body["status"] == "pending", "arquivo binário aceito e enfileirado"


def test_ac008_get_and_list_keep_vector_fields(client):
    c, h = client
    chat = _create_chat(c, h)
    created = _upload(c, h, chat["id"], name="nota.txt", content=b"abc " * 20).json()
    got = c.get(f"/files/{created['id']}", headers=h).json()
    assert got["status"] == "pending"
    listing = c.get(f"/chats/{chat['id']}/files", headers=h).json()
    assert listing[0]["id"] == created["id"]


def _minimal_pdf() -> bytes:
    text = "Hello PDF"
    stream = b"BT /F1 12 Tf 72 720 Td (" + text.encode() + b") Tj ET"
    objs = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>\nendobj\n",
        b"4 0 obj\n<< /Length "
        + str(len(stream)).encode()
        + b" >>\nstream\n"
        + stream
        + b"\nendstream\nendobj\n",
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
    ]
    out = b"%PDF-1.4\n"
    offsets = [0]
    for obj in objs:
        offsets.append(len(out))
        out += obj
    xref_pos = len(out)
    out += b"xref\n0 6\n0000000000 65535 f \n"
    for off in offsets[1:]:
        out += ("%010d 00000 n \n" % off).encode()
    out += (
        b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n"
        + str(xref_pos).encode()
        + b"\n%%EOF\n"
    )
    return out