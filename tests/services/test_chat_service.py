"""Testes TDD da feature F-005 (ChatService) — adaptado ao ownership (F-012).

Valida AC-001 e AC-004/AC-005: service orquestra com repositório e trata
chat inexistente; dependency get_session exposta e utilizável.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from einstein_test.db.base import Base
from einstein_test.models.chat import Chat
from einstein_test.repositories import ChatRepositorySQLAlchemy
from einstein_test.services.chat import ChatNotFoundError, ChatService


class _SentinelRepo:
    """ChatRepository fake simples para testar o service isolado."""

    def __init__(self, chats=None):
        self._chats = chats or {}
        self._next_id = 1

    def create(self, user_id, name, description=None):
        chat = Chat(
            id=self._next_id, user_id=user_id, name=name, description=description
        )
        self._chats[self._next_id] = chat
        self._next_id += 1
        return chat

    def get_by_id(self, chat_id, user_id):
        chat = self._chats.get(chat_id)
        if chat is None or chat.deleted_at is not None:
            return None
        if chat.user_id != user_id:
            return None
        return chat

    def list(self, user_id, *, limit=None, offset=None):
        items = [
            c for c in self._chats.values()
            if c.deleted_at is None and c.user_id == user_id
        ]
        if offset is not None:
            items = items[offset:]
        if limit is not None:
            items = items[:limit]
        return items

    def count(self, user_id):
        return len([
            c for c in self._chats.values()
            if c.deleted_at is None and c.user_id == user_id
        ])

    def delete(self, chat_id):
        chat = self._chats.get(chat_id)
        if chat is not None:
            from datetime import UTC, datetime
            chat.deleted_at = datetime.now(UTC)
        return None


USER_ID = 7


def test_ac001_service_created_with_protocol_repo():
    repo = _SentinelRepo()
    service = ChatService(repo)
    assert service.repository is repo


def test_ac001_create_get_list_delete():
    repo = _SentinelRepo()
    service = ChatService(repo)

    created = service.create_chat(USER_ID, name="Chat", description="d")
    assert created.id is not None and created.name == "Chat"

    fetched = service.get_chat(created.id, USER_ID)
    assert fetched.name == "Chat"

    assert len(service.list_chats(USER_ID)) == 1

    service.delete_chat(created.id, USER_ID)
    with pytest.raises(ChatNotFoundError):
        service.get_chat(created.id, USER_ID)
    assert service.list_chats(USER_ID) == []


def test_ac001_chat_of_other_user_not_visible():
    repo = _SentinelRepo()
    service = ChatService(repo)
    created = service.create_chat(USER_ID, name="Chat")
    with pytest.raises(ChatNotFoundError):
        service.get_chat(created.id, USER_ID + 1)
    with pytest.raises(ChatNotFoundError):
        service.delete_chat(created.id, USER_ID + 1)
    assert service.list_chats(USER_ID + 1) == []


def test_ac001_service_delete_unknown_raises():
    repo = _SentinelRepo()
    service = ChatService(repo)
    with pytest.raises(ChatNotFoundError):
        service.delete_chat(999999, USER_ID)


def test_ac001_service_get_unknown_raises():
    repo = _SentinelRepo()
    service = ChatService(repo)
    with pytest.raises(ChatNotFoundError):
        service.get_chat(999999, USER_ID)


def test_ac004_get_session_yields_valid_session():
    from einstein_test.api.dependencies import configure_session_factory, get_session

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    configure_session_factory(engine)

    gen = get_session()
    session = next(gen)
    assert isinstance(session, Session)

    repo = ChatRepositorySQLAlchemy(session)
    chat = repo.create(user_id=USER_ID, name="Chat DB")
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