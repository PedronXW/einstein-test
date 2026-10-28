"""Storage da aplicação (object storage)."""

from einstein_test.storage.inmemory import InMemoryStorage
from einstein_test.storage.minio import MinioStorage, Storage

_storage: Storage | None = None


def parse_s3_url(url: str) -> tuple[str, str] | None:
    """Converte `s3://<bucket>/<key>` em (bucket, key); None se inválido."""
    if not url or not url.startswith("s3://"):
        return None
    parts = url.split("/", 3)
    if len(parts) < 4:
        return None
    return parts[2], parts[3]


def get_storage() -> Storage:
    """Retorna o storage configurado (MinIO por padrão; fake nos testes)."""
    global _storage
    if _storage is None:
        _storage = MinioStorage()
    return _storage


def set_storage(storage: Storage) -> None:
    global _storage
    _storage = storage


__all__ = [
    "InMemoryStorage",
    "MinioStorage",
    "Storage",
    "get_storage",
    "set_storage",
    "parse_s3_url",
]