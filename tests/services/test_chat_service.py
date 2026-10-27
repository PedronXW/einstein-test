"""Testes TDD da feature F-005 (ChatService).

Valida AC-001 e AC-004/AC-005: service orquestra com repositório e trata
chat inexistente; dependency get_session exposta e utilizável.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from einstein_test.db.base import Base
from einstein_test.models.chat import Chat
from einstein_test.repositories import ChatRepository, ChatRepositorySQLAlchemy
from einstein_test.services.chat import ChatNotFoundError, ChatService


class _SentinelRepo:
    """ChatRepository fake simples para testar o service isolado."""

    def __init__(self, chats=None):
        self._chats = chats or {}
        self._next_id = 1

    def create(self, name, description=None):
        chat = Chat(id=self._next_id, name=name, description=description)
        self._chats[self._next_id] = chat
        self._next_id += 1
        return chat

    def get_by_id(self, chat_id):
        chat = self._chats.get(chat_id)
        if chat is not None and chat.deleted_at is not None:
            return None
        return chat

    def list(self):
        return [c for c in self._chats.values() if c.deleted_at is None]

    def delete(self, chat_id):
        chat = self._chats.get(chat_id)
        if chat is not None:
            from datetime import UTC, datetime
            chat.deleted_at = datetime.now(UTC)
        return None


def test_ac001_service_created_with_protocol_repo():
    repo = _SentinelRepo()
    service = ChatService(repo)
    assert service.repository is repo


def test_ac001_create_get_list_delete():
    repo = _SentinelRepo()
    service = ChatService(repo)

    created = service.create_chat(name="Chat", description="d")
    assert created.id is not None and created.name == "Chat"

    fetched = service.get_chat(created.id)
    assert fetched.name == "Chat"

    assert len(service.list_chats()) == 1

    service.delete_chat(created.id)
    with pytest.raises(ChatNotFoundError):
        service.get_chat(created.id)
    assert service.list_chats() == []


def test_ac001_service_delete_unknown_raises():
    repo = _SentinelRepo()
    service = ChatService(repo)
    with pytest.raises(ChatNotFoundError):
        service.delete_chat(999999)


def test_ac001_service_get_unknown_raises():
    repo = _SentinelRepo()
    service = ChatService(repo)
    with pytest.raises(ChatNotFoundError):
        service.get_chat(999999)


def test_ac004_get_session_yields_valid_session():
    from einstein_test.api.dependencies import configure_session_factory, get_session

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    configure_session_factory(engine)
    gen = get_session()
    session = next(gen)
    assert isinstance(session, Session)
    gen.close()
    with pytest.raises(StopIteration):
        next(gen)  # generator encerrou -> finally: session.close() rodou


def test_ac004_repository_works_against_sqlite():
    from einstein_test.api.dependencies import configure_session_factory, get_session

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    configure_session_factory(engine)
    gen = get_session()
    session = next(gen)

    repo = ChatRepositorySQLAlchemy(session)
    chat = repo.create(name="Chat DB")
    assert chat.id is not None

    gen.close()
    engine.dispose()


def test_ac004_session_dependency_default_engine():
    """get_session() não exige argumentos de request (assinatura sem obrigatórios)."""
    import inspect

    from einstein_test.api.dependencies import get_session

    sig = inspect.signature(get_session)
    required = [
        p for p in sig.parameters.values()
        if p.default is inspect.Parameter.empty
    ]
    assert required == [], "dependency get_session sem parâmetros obrigatórios de request"