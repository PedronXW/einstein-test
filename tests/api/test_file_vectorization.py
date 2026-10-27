"""Testes TDD da feature F-010 (AC-006/AC-008: upload síncrono vetoriza).

Valida que POST /chats/{chat_id}/files extrai texto, chunk, embed e persiste
vetores de forma síncrona — o FileRead retorna chunk_ids e vector_reference.
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
        yield c
    engine.dispose()


def _create_chat(client, name="Chat"):
    return client.post("/chats", json={"name": name}).json()


def _upload(client, chat_id, name="nota.txt", content=b"texto longo " * 30, type_="text/plain"):
    return client.post(
        f"/chats/{chat_id}/files",
        files={"file": (name, io.BytesIO(content), type_)},
    )


def test_ac006_upload_vectorizes_synchronously(client):
    chat = _create_chat(client)
    resp = _upload(client, chat["id"])
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["chunk_ids"], list), "FileRead expõe chunk_ids"
    assert body["chunk_ids"], "upload vetoriza e retorna chunk_ids na hora"
    assert body["vector_reference"], "FileRead expõe vector_reference"


def test_ac006_upload_pdf_vectorizes(client):
    chat = _create_chat(client)
    resp = _upload(client, chat["id"], name="doc.pdf", content=_minimal_pdf(), type_="application/pdf")
    assert resp.status_code == 200
    body = resp.json()
    assert body["chunk_ids"], "PDF vetorizado de forma síncrona no upload"


def test_ac006_read_shape_includes_vector_fields(client):
    chat = _create_chat(client)
    body = _upload(client, chat["id"], name="shape.txt", content=b"abc " * 5).json()
    assert {"chunk_ids", "vector_reference"} <= set(body)


def test_ac006_upload_non_text_empty_chunk_ids(client):
    chat = _create_chat(client)
    body = _upload(client, chat["id"], name="img.png", content=b"\x89PNG", type_="image/png").json()
    assert body["chunk_ids"] == [], "arquivo binário sem texto -> chunk_ids vazio"


def test_ac008_get_and_list_keep_vector_fields(client):
    chat = _create_chat(client)
    created = _upload(client, chat["id"], name="nota.txt", content=b"abc " * 20).json()
    got = client.get(f"/files/{created['id']}").json()
    assert got["chunk_ids"] == created["chunk_ids"]
    listing = client.get(f"/chats/{chat['id']}/files").json()
    assert listing[0]["vector_reference"] == created["vector_reference"]


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