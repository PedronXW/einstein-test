"""Implementação in-memory de Storage (testes)."""

from app.storage.minio import Storage


class InMemoryStorage:
    """Guarda bytes em memória; retorna url determinística (testes)."""

    bucket = "einstein"

    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    def upload(
        self, bucket: str, path: str, content: bytes, content_type: str | None = None
    ) -> str:
        self._objects[path] = content
        return f"s3://{bucket}/{path}"

    def delete(self, bucket: str, path: str) -> None:
        self._objects.pop(path, None)