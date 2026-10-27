"""Serviço de File — orquestra upload (storage) e persistência (metadata)."""

import re
import uuid
from pathlib import PurePath

from einstein_test.models.file import File
from einstein_test.repositories import FileRepository
from einstein_test.storage import Storage, get_storage

SAFE_NAME_PATTERN = re.compile(r"^[\w.\- ]{1,255}$")


class FileNotFound(LookupError):
    """Lançada quando um file não existe."""


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
    ) -> None:
        self.repository: FileRepository = repository
        self.storage: Storage = storage or get_storage()

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
            return self.repository.create(
                chat_id=chat_id,
                name=safe_name,
                url=url,
                type=content_type,
                size=len(content),
            )
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
        self.repository.delete(file_id)
        if file_.url and file_.url.startswith(f"s3://{self.storage.bucket}/"):
            self.storage.delete(self.storage.bucket, file_.url.split("/", 3)[3])