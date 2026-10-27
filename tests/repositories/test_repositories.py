"""Testes TDD da feature F-004 (repositories Chat e File).

Valida AC-004/AC-005: Protocol + implementação SQLAlchemy com CRUD (create,
get_by_id, list, soft delete) contra SQLite :memory: com create_all da Base.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from einstein_test.db.base import Base
from einstein_test.models.chat import Chat
from einstein_test.models.file import File
from einstein_test.repositories import (
    ChatRepository,
    ChatRepositorySQLAlchemy,
    FileRepository,
    FileRepositorySQLAlchemy,
)


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as sess:
        yield sess


def test_ac004_protocols_defined():
    import inspect

    assert inspect.isabstract(ChatRepository) or hasattr(
        ChatRepository, "__protocol_attrs__"
    ), "ChatRepository é Protocol"
    assert hasattr(ChatRepository, "create")
    assert hasattr(ChatRepository, "get_by_id")
    assert hasattr(ChatRepository, "list")
    assert hasattr(ChatRepository, "delete")
    assert hasattr(FileRepository, "create")
    assert hasattr(FileRepository, "get_by_id")
    assert hasattr(FileRepository, "list")
    assert hasattr(FileRepository, "delete")


def test_ac005_chat_crud(session):
    repo = ChatRepositorySQLAlchemy(session)
    chat = repo.create(name="Chat Teste", description="desc")
    assert chat.id is not None
    assert chat.name == "Chat Teste"

    fetched = repo.get_by_id(chat.id)
    assert fetched is not None and fetched.id == chat.id

    chats = repo.list()
    assert any(c.id == chat.id for c in chats)

    repo.delete(chat.id)
    assert repo.get_by_id(chat.id) is None
    # soft delete: registro continua na tabela com deleted_at preenchido
    deleted = session.get(Chat, chat.id)
    assert deleted is not None and deleted.deleted_at is not None


def test_ac005_file_crud(session):
    chat_repo = ChatRepositorySQLAlchemy(session)
    chat = chat_repo.create(name="Chat com file")
    file_repo = FileRepositorySQLAlchemy(session)

    file_ = file_repo.create(
        chat_id=chat.id,
        name="relatorio.pdf",
        url="s3://bucket/relatorio.pdf",
        type="application/pdf",
        size=1024,
    )
    assert file_.id is not None
    assert file_.chat_id == chat.id

    fetched = file_repo.get_by_id(file_.id)
    assert fetched is not None and fetched.name == "relatorio.pdf"

    files = file_repo.list(chat_id=chat.id)
    assert any(f.id == file_.id for f in files)

    file_repo.delete(file_.id)
    assert file_repo.get_by_id(file_.id) is None
    deleted = session.get(File, file_.id)
    assert deleted is not None and deleted.deleted_at is not None
    assert all(f.id != file_.id for f in file_repo.list(chat_id=chat.id)), (
        "list() nao retorna registro soft-deletado"
    )


def test_ac005_defaults_and_missing_id(session):
    chat_repo = ChatRepositorySQLAlchemy(session)
    chat = chat_repo.create(name="Chat defaults")
    file_repo = FileRepositorySQLAlchemy(session)

    file_ = file_repo.create(chat_id=chat.id, name="min.txt", url="s3://b/min.txt")
    assert file_.size == 0, "size default 0"
    assert file_.type is None, "type default None"

    assert chat_repo.get_by_id(999999) is None, "chat inexistente -> None"
    assert file_repo.get_by_id(999999) is None, "file inexistente -> None"
    chat_repo.delete(999999)  # no-op sem erro
    file_repo.delete(999999)  # no-op sem erro