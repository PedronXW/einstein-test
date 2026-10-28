"""Testes de integração (F-024): fluxo real via provedor OpenAI-compatível.

RODADO APENAS com `RUN_INTEGRATION=1` (e infra postgres/minio/redis de pé) —
senão, skip gracioso. Valida: upload real → vetorização (embeddings) → status
ready → pergunta → SSE streaming com [DONE] e assistant salva.
"""

import io
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from einstein_test.db.base import Base
from einstein_test.main import create_app
from einstein_test.storage import set_storage, InMemoryStorage

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def integration_available():
    """Skipa se a integração não estiver configurada (chave + flag + infra)."""
    if os.getenv("RUN_INTEGRATION") != "1":
        pytest.skip("RUN_INTEGRATION != 1 — integração desabilitada")
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY ausente — integração desabilitada")
    return True


@pytest.fixture
def client(integration_available):
    # app com postgres real (DATABASE_URL do ambiente) e storage fake em memória
    # (o upload usa minio real se configurado; aqui usamos InMemory para simplicidade)
    from einstein_test.api.dependencies import configure_session_factory

    engine = create_engine(os.getenv("DATABASE_URL", "postgresql://einstein:einstein@localhost:5432/einstein"))
    Base.metadata.create_all(engine)
    configure_session_factory(engine)
    set_storage(InMemoryStorage())
    app = create_app()
    app.dependency_overrides.clear()
    with TestClient(app) as c:
        yield c
    engine.dispose()


def _register_and_login(client):
    email = f"int_{os.getpid()}@b.com"
    client.post("/users", json={"email": email, "password": "senha123"})
    resp = client.post("/auth/login", json={"email": email, "password": "senha123"})
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_rag_end_to_end(client):
    h = _register_and_login(client)
    chat = client.post("/chats", json={"name": "int"}, headers=h).json()
    chat_id = chat["id"]

    # 1) upload de um arquivo texto
    content = ("saúde mental na atenção primária. " * 50).encode()
    up = client.post(
        f"/chats/{chat_id}/files",
        files={"file": ("saude.txt", io.BytesIO(content), "text/plain")},
        headers=h,
    )
    assert up.status_code == 202, f"upload: {up.text}"
    file_id = up.json()["id"]

    # 2) aguarda vetorização real (worker ou execução manual) ficar ready
    import time

    for _ in range(60):
        got = client.get(f"/files/{file_id}", headers=h).json()
        if got["status"] == "ready":
            break
        time.sleep(1)
    assert got["status"] == "ready", f"arquivo não vetorizou: {got}"

    # 3) pergunta real com LLM real → SSE com [DONE] e assistant salva
    resp = client.post(
        f"/chats/{chat_id}/messages",
        json={"content": "O que é saúde mental na atenção primária?"},
        headers={**h, "Accept": "text/event-stream"},
    )
    assert resp.status_code == 200
    body = resp.text
    assert "[DONE]" in body, "SSE concluiu"
    assert '"message_id"' in body, "assistant salva com id"
    msgs = client.get(f"/chats/{chat_id}/messages", headers=h).json()
    assert any(m["role"] == "assistant" and m["content"] for m in msgs)