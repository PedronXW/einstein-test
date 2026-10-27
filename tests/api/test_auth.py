"""Testes TDD da feature F-012 (AC-002/AC-005/AC-006/AC-007/AC-008: API auth).

Valida POST /users, POST /auth/login, isolamento de chats entre usuários,
files/messages de chat alheio -> 404, e testes existentes adaptados com
fixture autenticado.
"""

import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from einstein_test.db.base import Base
from einstein_test.main import create_app


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

    from einstein_test.services.rag import FakeChatLLM, RagService, set_rag_factory
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
        yield c, engine

    from einstein_test.services.rag import reset_rag_factory

    reset_rag_factory()
    engine.dispose()


def _register(client, email, password="senha123"):
    return client.post("/users", json={"email": email, "password": password})


def _login(client, email, password="senha123"):
    return client.post("/auth/login", json={"email": email, "password": password})


def _auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def _register_and_login(client, email):
    _register(client, email)
    return _login(client, email).json()["access_token"]


def test_ac002_register_user(client):
    c, engine = client
    resp = _register(c, "novo@b.com")
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "novo@b.com"
    assert "password" not in body and "password_hash" not in body


def test_ac002_register_duplicate_409(client):
    c, engine = client
    _register(c, "dup@b.com")
    resp = _register(c, "dup@b.com")
    assert resp.status_code == 409, "email duplicado -> 409"


def test_ac002_register_invalid_email_422(client):
    c, engine = client
    resp = _register(c, "nao-e-email")
    assert resp.status_code == 422


def test_ac002_login_returns_token(client):
    c, engine = client
    _register(c, "login@b.com")
    resp = _login(c, "login@b.com")
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"], "token JWT presente"


def test_ac008_login_invalid_password_401(client):
    c, engine = client
    _register(c, "x@b.com")
    resp = _login(c, "x@b.com", password="errada")
    assert resp.status_code == 401


def test_ac008_login_unknown_user_401(client):
    c, engine = client
    resp = _login(c, "ghost@b.com")
    assert resp.status_code == 401


def test_ac005_chat_requires_auth(client):
    c, engine = client
    resp = c.get("/chats")
    assert resp.status_code == 401, "sem token -> 401"
    resp = c.post("/chats", json={"name": "x"})
    assert resp.status_code == 401


def test_ac005_chats_isolated_between_users(client):
    c, engine = client
    token_a = _register_and_login(c, "alice@b.com")
    token_b = _register_and_login(c, "bob@b.com")

    chat_a = c.post(
        "/chats", json={"name": "da alice"}, headers=_auth_headers(token_a)
    ).json()

    # bob não vê o chat da alice
    resp_b = c.get("/chats", headers=_auth_headers(token_b))
    assert resp_b.json() == [], "bob lista só os próprios chats"

    # bob não acessa o chat da alice por id
    resp = c.get(f"/chats/{chat_a['id']}", headers=_auth_headers(token_b))
    assert resp.status_code == 404, "chat alheio -> 404 (não vaza existência)"
    resp = c.delete(f"/chats/{chat_a['id']}", headers=_auth_headers(token_b))
    assert resp.status_code == 404


def test_ac005_owner_access_ok(client):
    c, engine = client
    token = _register_and_login(c, "dona@b.com")
    chat = c.post(
        "/chats", json={"name": "meu"}, headers=_auth_headers(token)
    ).json()
    assert c.get("/chats", headers=_auth_headers(token)).json()[0]["id"] == chat["id"]
    assert c.get(f"/chats/{chat['id']}", headers=_auth_headers(token)).status_code == 200


def test_ac006_files_and_messages_isolated(client):
    c, engine = client
    token_a = _register_and_login(c, "alice2@b.com")
    token_b = _register_and_login(c, "bob2@b.com")
    chat_a = c.post(
        "/chats", json={"name": "arquivos"}, headers=_auth_headers(token_a)
    ).json()

    # bob não lista/envia mensagens nem arquivos no chat da alice
    assert c.get(
        f"/chats/{chat_a['id']}/messages", headers=_auth_headers(token_b)
    ).status_code == 404
    assert c.post(
        f"/chats/{chat_a['id']}/messages",
        json={"content": "oi"},
        headers=_auth_headers(token_b),
    ).status_code == 404
    assert c.get(
        f"/chats/{chat_a['id']}/files", headers=_auth_headers(token_b)
    ).status_code == 404


def test_ac007_messages_without_files_still_work(client):
    # chat sem arquivos: RAG responde com contexto vazio (não quebra)
    c, engine = client
    token = _register_and_login(c, "semarq@b.com")
    chat = c.post("/chats", json={"name": "vazio"}, headers=_auth_headers(token)).json()
    resp = c.post(
        f"/chats/{chat['id']}/messages",
        json={"content": "pergunta"},
        headers=_auth_headers(token),
    )
    assert resp.status_code == 200
    assert "[DONE]" in resp.text


def test_ac006_idor_files_by_id_blocked(client):
    # usuário B não pode GET/DELETE /files/{id} de um arquivo de A
    c, engine = client
    token_a = _register_and_login(c, "alicefiles@b.com")
    token_b = _register_and_login(c, "bobfiles@b.com")
    chat_a = c.post(
        "/chats", json={"name": "arq"}, headers=_auth_headers(token_a)
    ).json()
    created = c.post(
        f"/chats/{chat_a['id']}/files",
        files={"file": ("nota.txt", io.BytesIO(b"texto curto"), "text/plain")},
        headers=_auth_headers(token_a),
    ).json()
    assert c.get(f"/files/{created['id']}", headers=_auth_headers(token_a)).status_code == 200
    assert c.get(f"/files/{created['id']}", headers=_auth_headers(token_b)).status_code == 404
    assert c.delete(f"/files/{created['id']}", headers=_auth_headers(token_b)).status_code == 404
    # owner ainda vê (não foi deletado)
    assert c.get(f"/files/{created['id']}", headers=_auth_headers(token_a)).status_code == 200


def test_ac006_idor_messages_by_id_blocked(client):
    # usuário B não pode GET/DELETE /messages/{id} de uma mensagem de A
    c, engine = client
    token_a = _register_and_login(c, "alicemsg@b.com")
    token_b = _register_and_login(c, "bobmsg@b.com")
    chat_a = c.post(
        "/chats", json={"name": "msg"}, headers=_auth_headers(token_a)
    ).json()
    resp = c.post(
        f"/chats/{chat_a['id']}/messages",
        json={"content": "pergunta do dono"},
        headers={**_auth_headers(token_a), "Accept": "text/event-stream"},
    )
    import re
    m = re.search(r'data:\s*\{"message_id":\s*(\d+)\}', resp.text)
    assert m, "message_id presente no SSE"
    msg_id = int(m.group(1))
    assert c.get(f"/messages/{msg_id}", headers=_auth_headers(token_a)).status_code == 200
    assert c.get(f"/messages/{msg_id}", headers=_auth_headers(token_b)).status_code == 404
    assert c.delete(f"/messages/{msg_id}", headers=_auth_headers(token_b)).status_code == 404
    assert c.get(f"/messages/{msg_id}", headers=_auth_headers(token_a)).status_code == 200


def test_ac006_files_messages_routers_require_auth(client):
    c, engine = client
    assert c.get("/files/1").status_code == 401
    assert c.get("/messages/1").status_code == 401
    assert c.post(
        "/chats/1/files",
        files={"file": ("a.txt", io.BytesIO(b"x"), "text/plain")},
    ).status_code == 401