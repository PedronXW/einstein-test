"""Testes TDD da feature F-034 (AC-004/AC-005/AC-006: validações de upload no service).

Valida que `FileService` rejeita arquivo vazio, extensão não permitida e nome
duplicado no mesmo chat (regra de negócio no service, não no controller).
"""

import pytest

from einstein_test.services.file import (
    FileService,
    UnsupportedFileTypeError,
    DuplicateFileError,
    EmptyFileError,
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

    def commit(self):
        return None


@pytest.fixture
def service():
    return FileService(_FakeFileRepository(), InMemoryStorage())


def test_ac004_create_file_rejects_empty(service):
    with pytest.raises(EmptyFileError):
        service.create_file(chat_id=1, name="vazio.txt", content=b"")


def test_ac004_create_file_accepts_non_empty(service):
    file_ = service.create_file(chat_id=1, name="ok.txt", content=b"conteudo")
    assert file_.size > 0


def test_ac005_create_file_rejects_unsupported_ext(service):
    with pytest.raises(UnsupportedFileTypeError):
        service.create_file(chat_id=1, name="virus.exe", content=b"MZ")


def test_ac005_create_file_accepts_txt(service):
    file_ = service.create_file(chat_id=1, name="nota.txt", content=b"texto")
    assert file_.name == "nota.txt"


def test_ac005_create_file_accepts_pdf(service):
    file_ = service.create_file(chat_id=1, name="relatorio.pdf", content=b"%PDF")
    assert file_.name == "relatorio.pdf"


def test_ac005_create_file_accepts_uppercase_ext(service):
    file_ = service.create_file(chat_id=1, name="RELATORIO.TXT", content=b"texto")
    assert file_.name == "RELATORIO.TXT"


def test_ac006_create_file_rejects_duplicate_name_case_insensitive(service):
    service.create_file(chat_id=1, name="nota.txt", content=b"a")
    with pytest.raises(DuplicateFileError):
        service.create_file(chat_id=1, name="NOTA.TXT", content=b"b")


def test_ac006_create_file_allows_same_name_in_other_chat(service):
    service.create_file(chat_id=1, name="nota.txt", content=b"a")
    file_ = service.create_file(chat_id=2, name="nota.txt", content=b"b")
    assert file_.chat_id == 2


def test_ac004_batch_reports_empty_as_failure(service):
    from einstein_test.services.file import BatchFileInput

    result = service.create_files_batch(chat_id=1, uploads=[
        BatchFileInput("vazio.txt", b"", "text/plain"),
        BatchFileInput("ok.txt", b"conteudo", "text/plain"),
    ])
    assert [f.name for f in result.created] == ["ok.txt"]
    assert [(f.index, f.reason) for f in result.failures] == [
        (0, "arquivo vazio")
    ]


def test_ac005_batch_reports_unsupported_as_failure(service):
    from einstein_test.services.file import BatchFileInput

    result = service.create_files_batch(chat_id=1, uploads=[
        BatchFileInput("malware.exe", b"MZ", "application/octet-stream"),
    ])
    assert result.created == []
    assert result.failures[0].reason == "tipo de arquivo não suportado"


def test_ac006_batch_reports_duplicate_as_failure(service):
    from einstein_test.services.file import BatchFileInput

    service.create_file(chat_id=1, name="nota.txt", content=b"a")
    result = service.create_files_batch(chat_id=1, uploads=[
        BatchFileInput("nota.txt", b"outro", "text/plain"),
    ])
    assert result.created == []
    assert result.failures[0].reason == "arquivo duplicado"
