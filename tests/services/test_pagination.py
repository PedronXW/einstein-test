"""Testes TDD da feature F-036 (AC-006 — repositórios/serviços com paginação).

Valida que `list()` dos repositórios ganha `limit`/`offset` opcionais + `count()`
e que os usos internos (histórico RAG, files_state) continuam com a lista
completa quando chamados sem paginação.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from einstein_test.models import User
from einstein_test.models.chat import Chat
from einstein_test.models.file import File
from einstein_test.models.message import Message
from einstein_test.repositories.chat import ChatRepositorySQLAlchemy
from einstein_test.repositories.file import FileRepositorySQLAlchemy
from einstein_test.repositories.message import MessageRepositorySQLAlchemy
from einstein_test.services.chat import ChatService
from einstein_test.services.file import FileService
from einstein_test.services.message import MessageService


@pytest.fixture
def session(session_factory):
    s: Session = session_factory()
    user = User(email="user@b.com", password_hash="x", model="azure/gpt-5-mini")
    s.add(user)
    s.commit()
    chat = Chat(user_id=user.id, name="chat")
    s.add(chat)
    s.commit()
    for i in range(6):
        s.add(Message(
            chat_id=chat.id,
            content=f"msg-{i:02d}",
            role="user",
            created_at=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=i),
        ))
        s.add(File(
            chat_id=chat.id,
            name=f"file-{i:02d}.txt",
            url=f"s3://einstein/file-{i:02d}.txt",
            size=i,
            created_at=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=i),
        ))
    s.commit()
    yield s, user, chat


def test_ac006_repo_list_default_returns_full(session):
    s, user, chat = session
    msgs = MessageRepositorySQLAlchemy(s).list(chat_id=chat.id)
    files = FileRepositorySQLAlchemy(s).list(chat_id=chat.id)
    chats = ChatRepositorySQLAlchemy(s).list(user_id=user.id)
    assert len(msgs) == 6, "list() sem paginação retorna tudo (usos internos intactos)"
    assert len(files) == 6
    assert len(chats) == 1


def test_ac006_repo_list_limit_offset(session):
    s, user, chat = session
    repo = MessageRepositorySQLAlchemy(s)
    first = repo.list(chat_id=chat.id, limit=2)
    assert [m.content for m in first] == ["msg-00", "msg-01"]
    second = repo.list(chat_id=chat.id, limit=2, offset=2)
    assert [m.content for m in second] == ["msg-02", "msg-03"]


def test_ac006_repo_count(session):
    s, user, chat = session
    assert MessageRepositorySQLAlchemy(s).count(chat_id=chat.id) == 6
    assert FileRepositorySQLAlchemy(s).count(chat_id=chat.id) == 6
    assert ChatRepositorySQLAlchemy(s).count(user_id=user.id) == 1


def test_ac006_repo_count_excludes_soft_deleted(session):
    s, user, chat = session
    first = s.query(Message).first()
    first.deleted_at = datetime(2026, 1, 1, tzinfo=UTC)
    s.commit()
    assert MessageRepositorySQLAlchemy(s).count(chat_id=chat.id) == 5


def test_ac006_service_list_messages_page(session):
    s, user, chat = session
    service = MessageService(MessageRepositorySQLAlchemy(s))
    items, total = service.list_messages_page(chat_id=chat.id, page=2, page_size=2)
    assert total == 6
    assert [m.content for m in items] == ["msg-02", "msg-03"]


def test_ac006_service_internal_full_list_unpaged(session):
    s, user, chat = session
    message_service = MessageService(MessageRepositorySQLAlchemy(s))
    file_service = FileService(FileRepositorySQLAlchemy(s))

    history = message_service.list_messages(chat_id=chat.id)
    assert len(history) == 6, "histórico do RAG continua completo (sem paginação)"

    state = file_service.files_state(chat_id=chat.id)
    assert sum(state.values()) == 6, "files_state (readiness) conta todos os arquivos"


def test_ac006_service_list_chats_page(session):
    s, user, chat = session
    service = ChatService(ChatRepositorySQLAlchemy(s))
    items, total = service.list_chats_page(user_id=user.id, page=1, page_size=1)
    assert total == 1
    assert len(items) == 1
    assert items[0].name == "chat"