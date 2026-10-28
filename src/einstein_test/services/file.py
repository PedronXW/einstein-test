"""Serviço de File — orquestra upload (storage) e persistência (metadata)."""

import re
import uuid
from pathlib import PurePath
from typing import NamedTuple

from einstein_test.logging_setup import get_logger
from einstein_test.models.file import File
from einstein_test.repositories import FileRepository
from einstein_test.storage import Storage, get_storage, parse_s3_url
from einstein_test.vector import (
    Embedder,
    TextChunker,
    TextExtractor,
    VectorRepository,
    get_embedder,
)

logger = get_logger("services.file")

MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_CHUNKS = 500
MAX_FILES_PER_BATCH = 20

FILE_STATUS_PENDING = "pending"
FILE_STATUS_READY = "ready"
FILE_STATUS_ERROR = "error"


class BatchFileInput:
    """Entrada de um arquivo candidato a upload (conteúdo já lido)."""

    __slots__ = ("name", "content", "content_type")

    def __init__(self, name: str, content: bytes, content_type: str | None) -> None:
        self.name = name
        self.content = content
        self.content_type = content_type


class FileUploadFailure(NamedTuple):
    """Falha de um arquivo individual dentro de um upload em lote."""

    index: int
    name: str
    reason: str


class FileBatchUploadResult:
    """Resultado parcial do upload em lote: criados + falhas por arquivo."""

    def __init__(self) -> None:
        self.created: list[File] = []
        self.failures: list[FileUploadFailure] = []


class FileNotFound(LookupError):
    """Lançada quando um file não existe."""


class FileTooLargeError(ValueError):
    """Lançada quando um arquivo excede MAX_UPLOAD_SIZE."""


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
        if len(content) > MAX_UPLOAD_SIZE:
            raise FileTooLargeError(
                f"arquivo excede {MAX_UPLOAD_SIZE} bytes (máximo por arquivo)"
            )
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

    def create_files_batch(
        self,
        chat_id: int,
        uploads: list[BatchFileInput],
    ) -> FileBatchUploadResult:
        """Cria um lote de arquivos (não atômico): válidos viram File criado,
        inválidos viram FileUploadFailure(index, name, reason) — nunca lança
        exceção por arquivo individual, o lote inteiro prossegue.
        """
        if len(uploads) > MAX_FILES_PER_BATCH:
            raise ValueError(f"máximo de {MAX_FILES_PER_BATCH} arquivos por chamada")
        result = FileBatchUploadResult()
        for index, upload in enumerate(uploads):
            safe_name = sanitize_name(upload.name)
            if len(upload.content) > MAX_UPLOAD_SIZE:
                result.failures.append(
                    FileUploadFailure(index, safe_name, "arquivo muito grande")
                )
                continue
            try:
                file_ = self.create_file(
                    chat_id=chat_id,
                    name=safe_name,
                    content=upload.content,
                    content_type=upload.content_type,
                )
            except Exception:  # noqa: BLE001
                logger.warning("falha ao criar arquivo no lote", extra={
                    "event": "batch_file_failed", "chat_id": chat_id,
                    "index": index, "file_name": safe_name,
                })
                result.failures.append(
                    FileUploadFailure(index, safe_name, "falha ao processar arquivo")
                )
                continue
            result.created.append(file_)
        return result

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
        loc = parse_s3_url(file_.url) if file_.url else None
        if loc is not None and loc[0] == self.storage.bucket:
            self.storage.delete(loc[0], loc[1])

    def vectorize_uploaded(self, file_id: int) -> str:
        """Orquestra a vetorização de um arquivo já em storage (task de fundo).

        Retorna o status resultante: `missing` (arquivo inexistente), `ready`
        (já vetorizado ou concluído agora) ou `error`. Persiste via repository.
        """
        file_ = self.repository.get_by_id(file_id)
        if file_ is None:
            return "missing"
        if file_.status == FILE_STATUS_READY:
            return FILE_STATUS_READY
        loc = parse_s3_url(file_.url)
        if loc is None:
            self.mark_error(file_id, "url inválida do arquivo")
            return FILE_STATUS_ERROR
        bucket, key = loc
        content = self.storage.download(bucket, key)
        chunk_ids, reference = self._vectorize(file_.id, file_.name, content)
        file_.chunk_ids = chunk_ids
        file_.vector_reference = reference
        file_.status = FILE_STATUS_READY
        file_.error_detail = None
        self.repository.update_chunk_ids(file_.id, chunk_ids, reference)
        self.repository.commit()
        logger.info("vetorização concluída", extra={
            "event": "vectorize_done", "file_id": file_id,
            "status": FILE_STATUS_READY, "chunks": len(chunk_ids),
        })
        return FILE_STATUS_READY

    def mark_error(self, file_id: int, error: str) -> None:
        """Marca File como error (não sobrescreve `ready`)."""
        file_ = self.repository.get_by_id(file_id)
        if file_ is None or file_.status == FILE_STATUS_READY:
            return
        file_.status = FILE_STATUS_ERROR
        file_.error_detail = error
        self.repository.commit()