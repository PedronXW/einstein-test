"""Implementação in-memory de Storage (testes)."""



class InMemoryStorage:
    """Guarda bytes em memória; retorna url determinística (testes)."""

    bucket = "einstein"

    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    def ensure_bucket(self, name: str | None = None) -> None:
        """Nada a garantir — o storage em memória sempre 'tem' o bucket."""

    def upload(
        self, bucket: str, path: str, content: bytes, content_type: str | None = None
    ) -> str:
        self._objects[path] = content
        return f"s3://{bucket}/{path}"

    def download(self, bucket: str, path: str) -> bytes:
        return self._objects[path]

    def delete(self, bucket: str, path: str) -> None:
        self._objects.pop(path, None)