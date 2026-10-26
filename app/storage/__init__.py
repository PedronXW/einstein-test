"""Storage da aplicação (object storage)."""

from app.storage.inmemory import InMemoryStorage
from app.storage.minio import MinioStorage, Storage

_storage: Storage | None = None


def get_storage() -> Storage:
    """Retorna o storage configurado (MinIO por padrão; fake nos testes)."""
    global _storage
    if _storage is None:
        _storage = MinioStorage()
    return _storage


def set_storage(storage: Storage) -> None:
    global _storage
    _storage = storage


__all__ = ["InMemoryStorage", "MinioStorage", "Storage", "get_storage", "set_storage"]