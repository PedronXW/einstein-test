"""Testes TDD da feature F-034 (AC-001/AC-002/AC-003: avisos SSE + pergunta em branco).

Valida que POST /messages:
- AC-001: em chat SEM arquivos ready emite `event: notice` ({code, message}) e
  NÃO chama o LLM nem cria mensagem assistant;
- AC-002: com arquivos ready + pending/error, streama normalmente e emite um
  notice extra com as contagens de processing/failed;
- AC-003: pergunta em branco (espaços) -> 422.
"""


import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from einstein_test.db.base import Base
from einstein_test.main import create_app
from einstein_test.models.file import File
from einstein_test.services.rag import FakeChatLLM, RagService, set_rag_factory
from einstein_test.storage import InMemoryStorage, set_storage
from tests.conftest import register_and_login


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    from einstein_test.api.dependencies import configure_session_factory

    configure_session_factory(engine)
    set_storage(InMemoryStorage())

    from einstein_test.vector import FakeEmbedder

    def _factory(*args, **kwargs):
        return RagService(
            llm=FakeChatLLM(),
            retriever=kwargs["retriever"],
            embedder=FakeEmbedder(),
        )

    set_rag_factory(_factory)

    app = create_app()
    app.dependency_overrides.clear()
    with TestClient(app) as c:
        h = register_and_login(c, email="msg@b.com")
        yield c, h, engine

    from einstein_test.services.rag import reset_rag_factory

    reset_rag_factory()
    engine.dispose()


def _chat(client, headers):
    return client.post("/chats", json={"name": "Chat"}, headers=headers).json()


def _add_file(session: Session, chat_id: int, name: str, status: str) -> File:
    f = File(
        chat_id=chat_id, name=name, url=f"s3://einstein/{name}", size=5,
        status=status,
    )
    session.add(f)
    session.commit()
    return f


def _ask(client, chat_id, headers, content="pergunta"):
    return client.post(
        f"/chats/{chat_id}/messages",
        json={"content": content},
        headers={**headers, "Accept": "text/event-stream"},
    )


def test_ac001_no_ready_files_emits_notice_no_llm(client):
    c, h, engine = client
    chat = _chat(c, h)
    resp = _ask(c, chat["id"], h)
    assert resp.status_code == 200
    body = resp.text
    assert "notice" in body, "evento notice presente"
    assert "no_ready_files" in body, "código no_ready_files"
    assert '"token1"' not in body, "LLM não chamado"
    assert "[DONE]" not in body, "sem fluxo normal"
    msgs = c.get(f"/chats/{chat['id']}/messages", headers=h).json()["items"]
    roles = [m["role"] for m in msgs]
    assert "user" in roles, "mensagem do usuário salva"
    assert "assistant" not in roles, "nenhuma assistant criada"


def test_ac002_pending_only_notice_processing(client):
    c, h, engine = client
    chat = _chat(c, h)
    with Session(engine) as s:
        _add_file(s, chat["id"], "a.txt", "pending")
    resp = _ask(c, chat["id"], h)
    assert resp.status_code == 200
    assert "notice" in resp.text
    assert "no_ready_files" in resp.text
    assert '"token1"' not in resp.text


def test_ac002_mix_ready_and_pending_streams_with_notice(client):
    c, h, engine = client
    chat = _chat(c, h)
    with Session(engine) as s:
        _add_file(s, chat["id"], "pronto.txt", "ready")
        _add_file(s, chat["id"], "processando.txt", "pending")
        _add_file(s, chat["id"], "falhou.txt", "error")
    resp = _ask(c, chat["id"], h)
    assert resp.status_code == 200
    body = resp.text
    assert '"token1"' in body, "LLM chamado (tem ready)"
    assert "notice" in body, "aviso de estados parciais"
    assert "partial_files" in body, "código partial_files"
    assert '"processing": 1' in body, "contagem de processando"
    assert '"failed": 1' in body, "contagem de falhas"


def test_ac002_all_ready_no_notice(client):
    c, h, engine = client
    chat = _chat(c, h)
    with Session(engine) as s:
        _add_file(s, chat["id"], "pronto.txt", "ready")
    resp = _ask(c, chat["id"], h)
    assert resp.status_code == 200
    body = resp.text
    assert '"token1"' in body, "LLM chamado"
    assert "notice" not in body, "fluxo todo pronto não emite notice"


def test_ac003_blank_question_422(client):
    c, h, engine = client
    chat = _chat(c, h)
    resp = _ask(c, chat["id"], h, content="   ")
    assert resp.status_code == 422, "pergunta só de espaços -> 422"
