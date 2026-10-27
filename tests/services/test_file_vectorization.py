"""Testes TDD da feature F-010 (AC-005/AC-008: service vetoriza + File model).

Valida que FileService.create_file, com vector_repository + embedder fake,
extrai texto, chunk, embed e persiste vetores, populando chunk_ids e
vector_reference no model File.
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from einstein_test.db.base import Base
from einstein_test.models.file import File
from einstein_test.repositories import FileRepositorySQLAlchemy, VectorRepositorySQLAlchemy
from einstein_test.services.file import FileService
from einstein_test.storage import InMemoryStorage
from einstein_test.vector import FakeEmbedder, TextChunker, TextExtractor, VectorRepository


class _FakeFileRepository:
    def __init__(self):
        self._files = {}
        self._next_id = 1

    def create(self, chat_id, name, url, type=None, size=0, **extra):
        file_ = File(
            id=self._next_id, chat_id=chat_id, name=name,
            url=url, type=type, size=size, **extra,
        )
        self._files[self._next_id] = file_
        self._next_id += 1
        return file_

    def get_by_id(self, file_id):
        return self._files.get(file_id)

    def list(self, chat_id):
        return [f for f in self._files.values() if f.chat_id == chat_id]

    def update_chunk_ids(self, file_id, chunk_ids, vector_reference):
        f = self._files.get(file_id)
        if f is not None:
            f.chunk_ids = chunk_ids
            f.vector_reference = vector_reference

    def delete(self, file_id):
        f = self._files.get(file_id)
        if f is not None:
            f.deleted_at = datetime.now(UTC)


class _FakeVectorRepository:
    def __init__(self):
        self._chunks = {}

    def insert_chunks(self, file_id, chunks):
        ids = []
        for i, c in enumerate(chunks, start=1):
            self._chunks.setdefault(file_id, []).append({"id": i, **c})
            ids.append(i)
        return ids

    def get_chunks(self, file_id):
        return self._chunks.get(file_id, [])

    def delete_chunks(self, file_id):
        self._chunks.pop(file_id, None)

    def search_similar(self, embedding, chat_id, top_k=4):
        from einstein_test.vector.similarity import cosine_similarity_search

        rows = []
        for file_id, chunks in self._chunks.items():
            for c in chunks:
                c = dict(c)
                chunk = type(
                    "Chunk",
                    (),
                    {
                        "id": c["id"],
                        "file_id": file_id,
                        "content": c["content"],
                        "embedding": c["embedding"],
                    },
                )
                rows.append(chunk)
        return cosine_similarity_search(embedding, rows, top_k=top_k)


@pytest.fixture
def service():
    repo = _FakeFileRepository()
    vec = _FakeVectorRepository()
    svc = FileService(
        repo,
        InMemoryStorage(),
        vector_repository=vec,
        embedder=FakeEmbedder(),
        extractor=TextExtractor(),
        chunker=TextChunker(chunk_size=20, overlap=4),
    )
    return svc, repo, vec


def test_ac005_service_populates_chunk_ids_and_reference(service):
    svc, repo, vec = service
    file_ = svc.create_file(chat_id=1, name="nota.txt", content=b"palavra " * 10)
    assert file_.chunk_ids, "chunk_ids populados após vetorizar"
    assert file_.vector_reference, "vector_reference (UUID) populado"
    assert all(isinstance(i, int) for i in file_.chunk_ids)


def test_ac005_service_persists_vectors(service):
    svc, repo, vec = service
    file_ = svc.create_file(chat_id=1, name="nota.txt", content=b"conteudo " * 30)
    chunks = vec.get_chunks(file_.id)
    assert len(chunks) > 1, "texto longo gera múltiplos chunks vetorizados"
    assert chunks[0]["embedding"], "chunk guarda embedding"
    assert len(chunks[0]["embedding"]) == 1024, "embedding de 1024 dims"


def test_ac005_service_chunk_ids_match_saved(service):
    svc, repo, vec = service
    file_ = svc.create_file(chat_id=1, name="nota.txt", content=b"abc " * 5)
    saved = [c["id"] for c in vec.get_chunks(file_.id)]
    assert file_.chunk_ids == saved, "chunk_ids no File correspondem aos ids persistidos"


def test_ac005_service_txt_and_pdf_vectorized(service):
    svc, repo, vec = service
    txt = svc.create_file(chat_id=1, name="a.txt", content=b"texto puro " * 20)
    assert txt.chunk_ids
    pdf = svc.create_file(chat_id=1, name="b.pdf", content=_minimal_pdf(), content_type="application/pdf")
    assert pdf.chunk_ids, "PDF extraído via pypdf também é vetorizado"


def test_ac008_service_non_text_file_empty_chunks(service):
    svc, repo, vec = service
    file_ = svc.create_file(chat_id=1, name="img.png", content=b"\x89PNG data")
    assert file_.chunk_ids == [], "arquivo sem texto extraível -> sem vetores"


def test_ac008_service_rejects_too_many_chunks(service):
    svc, repo, vec = service
    with pytest.raises(Exception, match="chunks"):
        svc.create_file(chat_id=1, name="huge.txt", content=b"a" * 20000)


def test_ac008_service_delete_removes_vectors(service):
    svc, repo, vec = service
    file_ = svc.create_file(chat_id=1, name="nota.txt", content=b"x " * 10)
    assert vec.get_chunks(file_.id)
    svc.delete_file(file_.id)
    assert vec.get_chunks(file_.id) == [], "delete remove vetores do arquivo"


def test_ac008_sqlalchemy_vector_repo_integration():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        frepo = FileRepositorySQLAlchemy(session)
        file_ = frepo.create(chat_id=1, name="a.txt", url="s3://b/a.txt")
        vrepo = VectorRepositorySQLAlchemy(session)
        ids = vrepo.insert_chunks(
            file_.id,
            [{"index": 0, "content": "c", "embedding": [0.5] * 1024}],
        )
        got = vrepo.get_chunks(file_.id)
        assert [c.id for c in got] == ids
    engine.dispose()


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