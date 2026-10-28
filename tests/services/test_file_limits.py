"""Testes TDD da feature F-031 (AC-004: limites validados no service, não no controller).

Valida que `FileService.create_file` rejeita > MAX_UPLOAD_SIZE e que
`create_files_batch` rejeita > MAX_FILES_PER_BATCH — a regra mora no service.
"""

import pytest

from einstein_test.services.file import (
    MAX_FILES_PER_BATCH,
    BatchFileInput,
    FileTooLargeError,
    FileService,
)
from einstein_test.storage import InMemoryStorage


class _FakeFileRepository:
    def __init__(self):
        self._files = {}
        self._next_id = 1

    def create(self, chat_id, name, url, type=None, size=0):
        from einstein_test.models.file import File

        file_ = File(
            id=self._next_id, chat_id=chat_id, name=name,
            url=url, type=type, size=size,
        )
        self._files[self._next_id] = file_
        self._next_id += 1
        return file_

    def get_by_id(self, file_id):
        return self._files.get(file_id)

    def list(self, chat_id):
        return [f for f in self._files.values() if f.chat_id == chat_id]

    def update_chunk_ids(self, file_id, chunk_ids, vector_reference):
        return None

    def delete(self, file_id):
        self._files.pop(file_id, None)


def test_ac004_create_file_validates_max_upload_size(monkeypatch):
    import einstein_test.services.file as file_service

    monkeypatch.setattr(file_service, "MAX_UPLOAD_SIZE", 4)
    service = FileService(_FakeFileRepository(), InMemoryStorage())
    with pytest.raises(FileTooLargeError):
        service.create_file(chat_id=1, name="big.txt", content=b"x" * 100)


def test_ac004_create_file_accepts_at_limit(monkeypatch):
    import einstein_test.services.file as file_service

    monkeypatch.setattr(file_service, "MAX_UPLOAD_SIZE", 4)
    service = FileService(_FakeFileRepository(), InMemoryStorage())
    file_ = service.create_file(chat_id=1, name="ok.txt", content=b"abcd")
    assert file_.size == 4


def test_ac004_max_files_per_batch_lives_in_service():
    assert isinstance(MAX_FILES_PER_BATCH, int) and MAX_FILES_PER_BATCH == 20


def test_ac004_batch_rejects_over_max(monkeypatch):
    import einstein_test.services.file as file_service

    monkeypatch.setattr(file_service, "MAX_FILES_PER_BATCH", 2)
    service = FileService(_FakeFileRepository(), InMemoryStorage())
    uploads = [BatchFileInput(f"f{i}.txt", b"x", "text/plain") for i in range(3)]
    with pytest.raises(ValueError):
        service.create_files_batch(chat_id=1, uploads=uploads)
