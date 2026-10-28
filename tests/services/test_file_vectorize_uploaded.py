"""Testes TDD da feature F-031 (AC-005: FileService.vectorize_uploaded e task fina).

Valida que a orquestração de vetorização (carregar repo, baixar storage,
vetorizar, transicionar status, commit) vira método público de service, e que a
task Celery apenas invoca esse método.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from einstein_test.db.base import Base
from einstein_test.models.file import File
from einstein_test.repositories.file import FileRepositorySQLAlchemy
from einstein_test.services.file import FILE_STATUS_ERROR, FILE_STATUS_READY, FileService
from einstein_test.storage import InMemoryStorage
from einstein_test.vector import VectorRepositorySQLAlchemy


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()


def _service(session: Session, storage: InMemoryStorage, vector_repo) -> FileService:
    return FileService(
        FileRepositorySQLAlchemy(session),
        storage=storage,
        vector_repository=vector_repo,
    )


def test_ac005_vectorize_uploaded_marks_ready(session):
    from einstein_test.vector import FakeEmbedder

    storage = InMemoryStorage()
    file_ = _service(session, storage, None).create_file(
        chat_id=1, name="a.txt", content=b"hello world"
    )
    assert file_.status == "pending"

    service = _service(
        session,
        storage,
        VectorRepositorySQLAlchemy(session),
    )
    service.embedder = FakeEmbedder()
    status = service.vectorize_uploaded(file_.id)
    assert status == FILE_STATUS_READY
    session.commit()
    reloaded = session.get(File, file_.id)
    assert reloaded.status == FILE_STATUS_READY
    assert reloaded.chunk_ids != []


def test_ac005_vectorize_uploaded_missing_returns_missing(session):
    service = _service(session, InMemoryStorage(), VectorRepositorySQLAlchemy(session))
    assert service.vectorize_uploaded(999999) == "missing"


def test_ac005_vectorize_uploaded_ready_is_idempotent(session):
    from einstein_test.vector import FakeEmbedder

    storage = InMemoryStorage()
    service = _service(session, storage, VectorRepositorySQLAlchemy(session))
    service.embedder = FakeEmbedder()
    file_ = service.create_file(chat_id=1, name="a.txt", content=b"hello world")
    service.vectorize_uploaded(file_.id)
    second = service.vectorize_uploaded(file_.id)
    assert second == FILE_STATUS_READY


def test_ac005_mark_error_uses_service(session):
    from einstein_test.vector import FakeEmbedder

    storage = InMemoryStorage()
    service = _service(session, storage, VectorRepositorySQLAlchemy(session))
    service.embedder = FakeEmbedder()
    file_ = service.create_file(chat_id=1, name="a.txt", content=b"hello")
    service.mark_error(file_.id, "boom")
    session.commit()
    reloaded = session.get(File, file_.id)
    assert reloaded.status == FILE_STATUS_ERROR
    assert reloaded.error_detail == "boom"


def test_ac005_mark_error_does_not_overwrite_ready(session):
    from einstein_test.vector import FakeEmbedder

    storage = InMemoryStorage()
    service = _service(session, storage, VectorRepositorySQLAlchemy(session))
    service.embedder = FakeEmbedder()
    file_ = service.create_file(chat_id=1, name="a.txt", content=b"hello")
    service.vectorize_uploaded(file_.id)
    service.mark_error(file_.id, "boom")
    session.commit()
    reloaded = session.get(File, file_.id)
    assert reloaded.status == FILE_STATUS_READY, "ready não é sobrescrito por error"
