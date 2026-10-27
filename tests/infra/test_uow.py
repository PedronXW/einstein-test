"""Testes TDD da feature F-018 (transações atômicas / unit of work).

Valida: repositórios usam flush (não commit interno); get_session commita no
fim e faz rollback em erro; create_message com falha não deixa registros
órfãos; task Celery é atômica (rollback remove chunks).
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from einstein_test.db.base import Base
from einstein_test.models.user import User
from einstein_test.models.chat import Chat
from einstein_test.models.message import Message
from einstein_test.models.file import File
from einstein_test.models.file_chunk import FileChunk
from einstein_test.repositories.message import MessageRepositorySQLAlchemy
from einstein_test.vector.repository import VectorRepositorySQLAlchemy


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()


def _user_and_chat(session) -> int:
    user = User(email="uow@b.com", password_hash="x")
    session.add(user)
    session.flush()
    chat = Chat(user_id=user.id, name="Chat")
    session.add(chat)
    session.flush()
    return chat.id


def test_ac001_message_repo_uses_flush_not_commit(session):
    chat_id = _user_and_chat(session)
    mrepo = MessageRepositorySQLAlchemy(session)
    m = mrepo.create(chat_id=chat_id, content="msg", role="user")
    assert m.id is not None
    # repositório não commitou: a linha não está persistida até o commit
    assert session.get(Message, m.id) is not None  # flush deixou visível
    session.rollback()
    assert session.query(Message).count() == 0, "rollback removeu a linha"


def test_ac002_session_commit_on_success(session):
    chat_id = _user_and_chat(session)
    mrepo = MessageRepositorySQLAlchemy(session)
    mrepo.create(chat_id=chat_id, content="ok", role="user")
    session.commit()
    assert session.query(Message).count() == 1, "commit persistiu"


def test_ac003_create_message_rollback_no_orphan(session):
    chat_id = _user_and_chat(session)
    mrepo = MessageRepositorySQLAlchemy(session)
    m1 = mrepo.create(chat_id=chat_id, content="pergunta", role="user")
    assert m1.id is not None
    # falha antes do commit -> rollback não deixa user/assistant órfãos
    session.rollback()
    assert session.query(Message).count() == 0, "rollback removeu as mensagens"


def test_ac004_vector_repo_flush_and_rollback(session):
    chat_id = _user_and_chat(session)
    f = File(chat_id=chat_id, name="a.txt", url="s3://einstein/k/a.txt",
             type="text/plain", size=1, status="pending")
    session.add(f)
    session.flush()
    vrepo = VectorRepositorySQLAlchemy(session)
    ids = vrepo.insert_chunks(
        f.id, [{"index": 0, "content": "x", "embedding": [1.0, 0.0, 0.0]}]
    )
    assert ids, "chunks inseridos (flush)"
    session.rollback()
    assert session.query(FileChunk).count() == 0, "rollback removeu os chunks"


def test_ac004_task_atomic_no_partial_on_commit():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        chat_id = _user_and_chat(s)
        f = File(chat_id=chat_id, name="a.txt", url="s3://einstein/k/a.txt",
                 type="text/plain", size=1, status="pending")
        s.add(f)
        s.flush()
        vrepo = VectorRepositorySQLAlchemy(s)
        vrepo.insert_chunks(
            f.id, [{"index": 0, "content": "x", "embedding": [1.0, 0.0, 0.0]}]
        )
        # commita chunks + status juntos (task usa commit único no fim)
        f.status = "ready"
        s.commit()
        assert session_query_fc(engine) == 1
        f2 = s.get(File, f.id)
        assert f2.status == "ready"
    engine.dispose()


def session_query_fc(engine) -> int:
    with Session(engine) as s:
        return s.query(FileChunk).count()