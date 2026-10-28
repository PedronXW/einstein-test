"""Testes da garantia do bucket do storage no startup da aplicação.

Valida `MinioStorage.ensure_bucket` (idempotente e tolerante a indisponibilidade)
e que o lifespan do `create_app` chama `get_storage().ensure_bucket`.
"""

from typing import Any

import pytest
from botocore.exceptions import ClientError


class _FakeS3:
    """Fake do cliente boto3 focando apenas em head_bucket/create_bucket."""

    def __init__(
        self, exists: bool = False, fail_head: bool = False,
        create_error: Exception | None = None,
    ) -> None:
        self.exists = exists
        self.fail_head = fail_head
        self.created: list[str] = []
        self.head_calls = 0
        self.create_error = create_error

    def head_bucket(self, Bucket: str) -> None:
        self.head_calls += 1
        if self.fail_head:
            exc = ClientError(
                {"Error": {"Code": "500", "Message": "interno"}}, "HeadBucket"
            )
            raise exc
        if not self.exists:
            exc = ClientError(
                {"Error": {"Code": "404", "Message": "não existe"}}, "HeadBucket"
            )
            raise exc

    def create_bucket(self, Bucket: str) -> None:
        if self.create_error is not None:
            raise self.create_error
        self.created.append(Bucket)


def _minio(fake) -> Any:
    from einstein_test.storage.minio import MinioStorage

    storage = MinioStorage.__new__(MinioStorage)
    storage._s3 = fake
    storage.bucket = "einstein"
    return storage


def test_ensure_bucket_creates_when_missing():
    fake = _FakeS3(exists=False)
    storage = _minio(fake)

    storage.ensure_bucket()

    assert fake.head_calls == 1, "verifica a existência primeiro"
    assert fake.created == ["einstein"], "cria o bucket quando ausente"


def test_ensure_bucket_idempotent_when_exists():
    fake = _FakeS3(exists=True)
    storage = _minio(fake)

    storage.ensure_bucket()

    assert fake.head_calls == 1
    assert fake.created == [], "não recria bucket que já existe"


def test_ensure_bucket_accepts_custom_name():
    fake = _FakeS3(exists=False)
    storage = _minio(fake)

    storage.ensure_bucket(name="outro-bucket")

    assert fake.created == ["outro-bucket"]
    assert "einstein" not in fake.created


def test_ensure_bucket_raises_nonmissing_errors():
    # erro 5xx (não "bucket existe"/404) deve propagar — não é ausência
    fake = _FakeS3(fail_head=True)
    storage = _minio(fake)

    with pytest.raises(ClientError):
        storage.ensure_bucket()
    assert fake.created == [], "erro 5xx não deve criar bucket"


def test_ensure_bucket_nosuchbucket_code_creates():
    # head com NoSuchBucket também deve criar (não apenas "404")
    _orig = _FakeS3.head_bucket

    def _head_nosuch(self_, Bucket: str) -> None:
        exc = ClientError(
            {"Error": {"Code": "NoSuchBucket", "Message": "não existe"}},
            "HeadBucket",
        )
        raise exc

    _FakeS3.head_bucket = _head_nosuch  # type: ignore[assignment]
    try:
        fake = _FakeS3()
        storage = _minio(fake)
        storage.ensure_bucket()
        assert fake.created == ["einstein"]
    finally:
        _FakeS3.head_bucket = _orig  # type: ignore[assignment]


def test_ensure_bucket_race_creation_conflict_is_ok():
    # corrida: outro processo criou entre head(404) e create -> 409/AlreadyOwned
    from botocore.exceptions import ClientError as _CE

    conflict = _CE(
        {"Error": {"Code": "BucketAlreadyOwnedByYou", "Message": "conflito"}},
        "CreateBucket",
    )
    fake = _FakeS3(exists=False, create_error=conflict)
    storage = _minio(fake)

    storage.ensure_bucket()  # não levanta; conflito de criação é idempotente
    assert fake.created == []


def test_ensure_bucket_unavailable_connection_logs_and_returns():
    # MinIO fora do ar (erro de conexão, NÃO ClientError): loga e segue
    _orig = _FakeS3.head_bucket

    def _head_down(self_, Bucket: str) -> None:
        raise ConnectionError("connection refused")

    _FakeS3.head_bucket = _head_down  # type: ignore[assignment]
    try:
        fake = _FakeS3()
        storage = _minio(fake)
        storage.ensure_bucket()  # não levanta
        assert fake.created == [], "sem MinIO não tenta criar"
    finally:
        _FakeS3.head_bucket = _orig  # type: ignore[assignment]


def test_ensure_bucket_create_unavailable_connection_logs_and_returns():
    # create_bucket cai com erro de conexão: não deve derrubar o startup
    _orig = _FakeS3.head_bucket

    def _head_missing(self_, Bucket: str) -> None:
        exc = ClientError(
            {"Error": {"Code": "404", "Message": "não existe"}}, "HeadBucket"
        )
        raise exc

    _FakeS3.head_bucket = _head_missing  # type: ignore[assignment]
    try:
        fake = _FakeS3(exists=False)
        fake.create_error = ConnectionError("connection refused")
        storage = _minio(fake)
        storage.ensure_bucket()  # não levanta
    finally:
        _FakeS3.head_bucket = _orig  # type: ignore[assignment]


def test_inmemory_ensure_bucket_noop():
    from einstein_test.storage import InMemoryStorage

    storage = InMemoryStorage()
    storage.ensure_bucket()  # não levanta


def test_lifespan_calls_ensure_bucket(monkeypatch):
    """O startup do app chama get_storage().ensure_bucket()."""
    import einstein_test.storage as storage_mod

    called = {"n": 0}

    class _FakeStorage:
        def ensure_bucket(self, name: str | None = None) -> None:
            called["n"] += 1

    monkeypatch.setattr(storage_mod, "get_storage", lambda: _FakeStorage())

    monkeypatch.setenv("JWT_SECRET", "s" * 32)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("ALLOWED_MODELS", "azure/gpt-5-mini")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    from einstein_test.main import create_app

    app = create_app()
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        assert c.get("/health").status_code in (200, 307, 404)
    assert called["n"] >= 1, "startup chamou ensure_bucket"