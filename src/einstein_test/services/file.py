"""Serviço de File — orquestra upload (storage) e persistência (metadata)."""

import re
import uuid
from pathlib import PurePath

from einstein_test.models.file import File
from einstein_test.repositories import FileRepository
from einstein_test.storage import Storage, get_storage
from einstein_test.vector import (
    Embedder,
    TextChunker,
    TextExtractor,
    VectorRepository,
    get_embedder,
)

SAFE_NAME_PATTERN = re.compile(r"^[\w.\- ]{1,255}$")


MAX_CHUNKS = 500

SAFE_NAME_PATTERN = re.compile(r"^[\w.\- ]{1,255}$")


class FileNotFound(LookupError):
    """Lançada quando um file não existe."""


class VectorizationError(RuntimeError):
    """Lançada quando a vetorização do arquivo falha (chunks/embeddings inválidos)."""


def sanitize_name(name: str) -> str:
    """Normaliza o filename do cliente para um basename seguro (tamanho limitado)."""
    base = PurePath(name.replace("\\", "/")).name
    cleaned = re.sub(r"[\x00-\x1f]", "", base).strip()
    if not cleaned:
        cleaned = "arquivo"
    return cleaned[:255]


class FileService:
    def __init__(
        self,
        repository: FileRepository,
        storage: Storage | None = None,
        *,
        vector_repository: VectorRepository | None = None,
        embedder: Embedder | None = None,
        extractor: TextExtractor | None = None,
        chunker: TextChunker | None = None,
    ) -> None:
        self.repository: FileRepository = repository
        self.storage: Storage = storage or get_storage()
        self.vector_repository: VectorRepository | None = vector_repository
        self.embedder: Embedder | None = embedder
        self.extractor: TextExtractor = extractor or TextExtractor()
        self.chunker: TextChunker = chunker or TextChunker()

    def _embedder(self) -> Embedder:
        if self.embedder is not None:
            return self.embedder
        return get_embedder()

    def _vectorize(self, file_id: int, name: str, content: bytes) -> tuple[list[int], str]:
        """Extrai texto, chunk, embed e persiste vetores; retorna (chunk_ids, reference)."""
        reference = str(uuid.uuid4())
        if self.vector_repository is None:
            return [], reference
        text = self.extractor.extract(name, content)
        chunks = self.chunker.chunk(text)
        if not chunks:
            return [], reference
        if len(chunks) > MAX_CHUNKS:
            raise VectorizationError(
                f"arquivo gera {len(chunks)} chunks (máximo {MAX_CHUNKS})"
            )
        vectors = self._embedder().embed(chunks)
        if len(vectors) != len(chunks):
            raise VectorizationError(
                f"embedder retornou {len(vectors)} vetores para {len(chunks)} chunks"
            )
        rows = [
            {"index": i, "content": chunk, "embedding": vector}
            for i, (chunk, vector) in enumerate(zip(chunks, vectors))
        ]
        chunk_ids = self.vector_repository.insert_chunks(file_id, rows)
        return chunk_ids, reference

    def create_file(
        self,
        chat_id: int,
        name: str,
        content: bytes,
        content_type: str | None = None,
        *,
        key: str | None = None,
    ) -> File:
        safe_name = sanitize_name(name)
        object_key = key or f"chats/{chat_id}/{uuid.uuid4().hex}/{safe_name}"
        url = self.storage.upload(
            self.storage.bucket, object_key, content, content_type=content_type
        )
        try:
            file_ = self.repository.create(
                chat_id=chat_id,
                name=safe_name,
                url=url,
                type=content_type,
                size=len(content),
            )
            chunk_ids, reference = self._vectorize(file_.id, safe_name, content)
            file_.chunk_ids = chunk_ids
            file_.vector_reference = reference
            if self.vector_repository is not None:
                self.repository.update_chunk_ids(file_.id, chunk_ids, reference)
            return file_
        except Exception:
            self.storage.delete(self.storage.bucket, object_key)
            raise

    def get_file(self, file_id: int) -> File:
        file_ = self.repository.get_by_id(file_id)
        if file_ is None:
            raise FileNotFound(f"file {file_id} não encontrado")
        return file_

    def list_files(self, chat_id: int) -> list[File]:
        return self.repository.list(chat_id=chat_id)

    def delete_file(self, file_id: int) -> None:
        file_ = self.repository.get_by_id(file_id)
        if file_ is None:
            raise FileNotFound(f"file {file_id} não encontrado")
        if self.vector_repository is not None and file_.chunk_ids:
            self.vector_repository.delete_chunks(file_id)
        self.repository.delete(file_id)
        if file_.url and file_.url.startswith(f"s3://{self.storage.bucket}/"):
            self.storage.delete(self.storage.bucket, file_.url.split("/", 3)[3])