"""Testes TDD da feature F-007 (FileService + Storage + FileRepository).

Valida AC-001..AC-003: repository com list(chat_id), storage abstraído com
MinioStorage (boto3) e fake, service orquestrando.
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from einstein_test.db.base import Base
from einstein_test.models.file import File
from einstein_test.repositories import FileRepositorySQLAlchemy
from einstein_test.services.file import (
    BatchFileInput,
    FileBatchUploadResult,
    FileNotFound,
    FileService,
    FileUploadFailure,
)
from einstein_test.storage import InMemoryStorage, MinioStorage, Storage


class _FakeFileRepository:
    """FileRepository fake fiel ao Protocol (chat_id no list)."""

    def __init__(self):
        self._files = {}
        self._next_id = 1

    def create(self, chat_id, name, url, type=None, size=0):
        file_ = File(
            id=self._next_id, chat_id=chat_id, name=name,
            url=url, type=type, size=size,
        )
        self._files[self._next_id] = file_
        self._next_id += 1
        return file_

    def get_by_id(self, file_id):
        file_ = self._files.get(file_id)
        if file_ is not None and file_.deleted_at is not None:
            return None
        return file_

    def list(self, chat_id, *, limit=None, offset=None):
        items = [
            f for f in self._files.values()
            if f.chat_id == chat_id and f.deleted_at is None
        ]
        if offset is not None:
            items = items[offset:]
        if limit is not None:
            items = items[:limit]
        return items

    def count(self, chat_id):
        return len([
            f for f in self._files.values()
            if f.chat_id == chat_id and f.deleted_at is None
        ])

    def delete(self, file_id):
        file_ = self._files.get(file_id)
        if file_ is not None:
            file_.deleted_at = datetime.now(UTC)
        return None


def test_ac001_repository_list_filters_by_chat():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        repo = FileRepositorySQLAlchemy(session)
        repo.create(chat_id=1, name="a.txt", url="s3://b/a.txt")
        repo.create(chat_id=2, name="b.txt", url="s3://b/b.txt")
        assert [f.name for f in repo.list(chat_id=1)] == ["a.txt"]
        assert repo.list(chat_id=2) != []
        assert all(f.chat_id == 1 for f in repo.list(chat_id=1))
        assert repo.list(chat_id=999) == []
    engine.dispose()


def test_ac002_service_create_uses_storage():
    repo = _FakeFileRepository()
    storage = InMemoryStorage()
    service = FileService(repo, storage)

    file_ = service.create_file(
        chat_id=1, name="doc.pdf", content=b"%PDF",
        content_type="application/pdf",
    )
    assert file_.id is not None
    assert file_.chat_id == 1
    assert file_.type == "application/pdf"
    assert file_.size == 4
    assert file_.url  # url gerada pelo storage


def test_ac002_service_upload_stored_bytes():
    storage = InMemoryStorage()
    repo = _FakeFileRepository()
    service = FileService(repo, storage)

    file_ = service.create_file(chat_id=1, name="doc.pdf", content=b"hello")
    assert b"hello" in storage._objects.values(), "bytes persistidos no storage"
    assert file_.url.startswith("s3://einstein/chats/1/"), (
        "url aponta para o bucket/chat"
    )


def test_ac002_service_sanitizes_name_in_key():
    storage = InMemoryStorage()
    repo = _FakeFileRepository()
    service = FileService(repo, storage)

    file_ = service.create_file(
        chat_id=1, name="../../outro/aluno.pdf", content=b"x"
    )
    # a chave do objeto não contém traversal e o nome persistido é o basename
    assert ".." not in file_.url, "sem path traversal na chave do bucket"
    assert file_.name == "aluno.pdf", "nome persistido é o basename sanitizado"


def test_ac002_service_delete_removes_object_from_storage():
    storage = InMemoryStorage()
    repo = _FakeFileRepository()
    service = FileService(repo, storage)

    created = service.create_file(chat_id=1, name="rem.txt", content=b"data")
    object_key = created.url.split("/", 3)[3]
    assert object_key in storage._objects, "objeto existente no storage"

    service.delete_file(created.id)
    assert object_key not in storage._objects, "delete remove objeto do storage"


def test_ac002_service_get_list_delete():
    repo = _FakeFileRepository()
    service = FileService(repo, InMemoryStorage())
    created = service.create_file(chat_id=1, name="x.txt", content=b"x")

    assert service.get_file(created.id).name == "x.txt"
    assert len(service.list_files(chat_id=1)) == 1
    assert service.list_files(chat_id=2) == []

    service.delete_file(created.id)
    with pytest.raises(FileNotFound):
        service.get_file(created.id)
    assert service.list_files(chat_id=1) == []


def test_ac002_service_get_unknown_raises():
    service = FileService(_FakeFileRepository(), InMemoryStorage())
    with pytest.raises(FileNotFound):
        service.get_file(999999)


def test_ac002_service_delete_unknown_raises():
    service = FileService(_FakeFileRepository(), InMemoryStorage())
    with pytest.raises(FileNotFound):
        service.delete_file(999999)


def test_batch_all_valid_creates_each_file():
    repo = _FakeFileRepository()
    service = FileService(repo, InMemoryStorage())
    result = service.create_files_batch(chat_id=1, uploads=[
        BatchFileInput("a.txt", b"aaa", "text/plain"),
        BatchFileInput("b.pdf", b"%PDF", "application/pdf"),
    ])
    assert isinstance(result, FileBatchUploadResult)
    assert [f.name for f in result.created] == ["a.txt", "b.pdf"]
    assert result.failures == []
    assert len(service.list_files(chat_id=1)) == 2


def test_batch_over_limit_is_failure_not_creation(monkeypatch):
    import einstein_test.services.file as file_service

    monkeypatch.setattr(file_service, "MAX_UPLOAD_SIZE", 4)
    repo = _FakeFileRepository()
    service = FileService(repo, InMemoryStorage())
    result = service.create_files_batch(chat_id=1, uploads=[
        BatchFileInput("ok.txt", b"abc", "text/plain"),
        BatchFileInput("big.txt", b"x" * 100, "text/plain"),
    ])
    assert [f.name for f in result.created] == ["ok.txt"]
    assert result.failures == [
        FileUploadFailure(1, "big.txt", "arquivo muito grande")
    ]
    assert len(service.list_files(chat_id=1)) == 1


def test_batch_exception_maps_to_failure(monkeypatch):
    repo = _FakeFileRepository()
    storage = InMemoryStorage()
    service = FileService(repo, storage)

    def _boom(**kwargs):
        raise RuntimeError("storage fora do ar")

    monkeypatch.setattr(repo, "create", _boom)
    result = service.create_files_batch(chat_id=1, uploads=[
        BatchFileInput("a.txt", b"aaa", "text/plain"),
        BatchFileInput("b.txt", b"bb", "text/plain"),
    ])
    assert result.created == []
    assert result.failures == [
        FileUploadFailure(0, "a.txt", "falha ao processar arquivo"),
        FileUploadFailure(1, "b.txt", "falha ao processar arquivo"),
    ]


def test_ac003_storage_is_protocol():
    assert hasattr(Storage, "upload")


def test_ac003_minio_storage_configured():
    assert MinioStorage.bucket == "einstein", "bucket default do compose F-001"


def test_ac003_minio_storage_default_endpoint(monkeypatch):
    monkeypatch.delenv("MINIO_ENDPOINT", raising=False)
    sentinel = []

    class _FakeS3:
        def __init__(self, *args, **kwargs):
            sentinel.append(kwargs)
            self.put_object = lambda **kw: None
            self.delete_object = lambda **kw: None

    import boto3

    monkeypatch.setattr(boto3, "client", _FakeS3)
    MinioStorage()
    kwargs = sentinel[0]
    assert kwargs["endpoint_url"] == "http://localhost:9000", (
        "MinioStorage default aponta para o MinIO local (porta 9000)"
    )


def test_ac003_inmemory_storage_roundtrip():
    storage = InMemoryStorage()
    url = storage.upload("einstein", "path/x.txt", b"data")
    assert url.endswith("path/x.txt")
    assert storage._objects["path/x.txt"] == b"data"