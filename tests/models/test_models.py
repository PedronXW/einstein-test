"""Testes TDD da feature F-004 (models Chat, File, Message).

Valida AC-001..AC-003: models declarativas sobre a Base com colunas e relações.
Introspeta o metadata das models (sem tocar banco).
"""

from app.db.base import Base
from app.models import Chat, File, Message


def test_ac001_chat_columns():
    cols = {c.name for c in Chat.__table__.columns}
    assert {"id", "name", "description", "created_at", "updated_at", "deleted_at"} <= cols
    assert Chat.__table__.c.id.primary_key is True
    assert Chat.__table__.c.description.nullable is True


def test_ac001_chat_relationships():
    rels = Chat.__mapper__.relationships
    assert "messages" in rels, "Chat.messages -> Message"
    assert "files" in rels, "Chat.files -> File"


def test_ac001_chat_registered_on_base():
    assert "chats" in Base.metadata.tables, "tabela chats registrada na Base"


def test_ac002_file_columns():
    cols = {c.name for c in File.__table__.columns}
    assert {"id", "name", "url", "type", "size", "created_at",
            "updated_at", "deleted_at", "chat_id"} <= cols
    assert File.__table__.c.size.type.python_type is int


def test_ac002_file_chat_fk():
    assert "chat_id" in File.__table__.c
    fk = list(File.__table__.c.chat_id.foreign_keys)
    assert len(fk) == 1
    assert fk[0].column.table.name == "chats", "File.chat_id -> chats.id"


def test_ac002_file_registered_on_base():
    assert "files" in Base.metadata.tables, "tabela files registrada na Base"


def test_ac003_message_columns():
    cols = {c.name for c in Message.__table__.columns}
    assert {"id", "content", "role", "chat_id", "created_at",
            "updated_at", "deleted_at"} <= cols
    assert Message.__table__.c.role.nullable is True


def test_ac003_message_chat_fk():
    fk = list(Message.__table__.c.chat_id.foreign_keys)
    assert len(fk) == 1
    assert fk[0].column.table.name == "chats", "Message.chat_id -> chats.id"


def test_ac003_message_registered_on_base():
    assert "messages" in Base.metadata.tables, "tabela messages registrada na Base"


def test_models_importable_from_app():
    from app.models import Chat, File, Message  # noqa: F401

    from app.models import chat as chat_mod
    from app.models import file as file_mod
    from app.models import message as message_mod

    assert Chat is chat_mod.Chat, "app.models.Chat expoem a model chat"
    assert File is file_mod.File, "app.models.File expoem a model file"
    assert Message is message_mod.Message, "app.models.Message expoem a model message"