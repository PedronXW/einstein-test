"""Testes TDD da feature F-006 (MessageService + MessageRepository).

Valida AC-001 e AC-002: repository dedicado e service com CRUD delegando ao
repositório (fake fiel ao Protocol) e MessageNotFoundError.
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.message import Message
from app.repositories import MessageRepository, MessageRepositorySQLAlchemy
from app.services.message import MessageNotFoundError, MessageService


class _FakeMessageRepository:
    """MessageRepository fake fiel ao Protocol (soft delete)."""

    def __init__(self):
        self._messages = {}
        self._next_id = 1

    def create(self, chat_id, content, role=None):
        msg = Message(id=self._next_id, chat_id=chat_id, content=content, role=role)
        self._messages[self._next_id] = msg
        self._next_id += 1
        return msg

    def get_by_id(self, message_id):
        msg = self._messages.get(message_id)
        if msg is not None and msg.deleted_at is not None:
            return None
        return msg

    def list(self, chat_id):
        return [
            m for m in self._messages.values()
            if m.chat_id == chat_id and m.deleted_at is None
        ]

    def delete(self, message_id):
        msg = self._messages.get(message_id)
        if msg is not None:
            msg.deleted_at = datetime.now(UTC)
        return None


def test_ac001_message_repository_protocol_exists():
    assert hasattr(MessageRepository, "create")
    assert hasattr(MessageRepository, "get_by_id")
    assert hasattr(MessageRepository, "list")
    assert hasattr(MessageRepository, "delete")


def test_ac001_repository_sqlalchemy_crud():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        repo = MessageRepositorySQLAlchemy(session)
        msg = repo.create(chat_id=1, content="olá", role="user")
        assert msg.id is not None and msg.content == "olá"

        assert repo.get_by_id(msg.id) is not None
        listed = repo.list(chat_id=1)
        assert any(m.id == msg.id for m in listed)
        assert repo.list(chat_id=2) == [], (
            "list filtra por chat_id (negativo)"
        )

        repo.delete(msg.id)
        assert repo.get_by_id(msg.id) is None
        assert repo.list(chat_id=1) == []
    engine.dispose()


def test_ac002_service_create_get_list_delete():
    repo = _FakeMessageRepository()
    service = MessageService(repo)

    created = service.create_message(chat_id=1, content="oi", role="user")
    assert created.id is not None and created.chat_id == 1

    fetched = service.get_message(created.id)
    assert fetched.content == "oi"

    assert len(service.list_messages(chat_id=1)) == 1

    service.delete_message(created.id)
    with pytest.raises(MessageNotFoundError):
        service.get_message(created.id)
    assert service.list_messages(chat_id=1) == []


def test_ac002_service_get_unknown_raises():
    service = MessageService(_FakeMessageRepository())
    with pytest.raises(MessageNotFoundError):
        service.get_message(999999)


def test_ac002_service_delete_unknown_raises():
    service = MessageService(_FakeMessageRepository())
    with pytest.raises(MessageNotFoundError):
        service.delete_message(999999)


def test_ac002_service_list_empty_chat():
    service = MessageService(_FakeMessageRepository())
    assert service.list_messages(chat_id=42) == []