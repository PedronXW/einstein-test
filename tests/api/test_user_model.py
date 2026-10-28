"""Testes TDD da feature F-022 (seleção de modelo por usuário).

Valida: User.model (nullable), GET/PATCH /users/me, ALLOWED_MODELS via env,
e get_rag_service criando adapter por usuário com o model (sem singleton LLM).
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from einstein_test.db.base import Base
from einstein_test.main import create_app
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
    app = create_app()
    app.dependency_overrides.clear()
    with TestClient(app) as c:
        headers = register_and_login(c, email="model@b.com")
        yield c, headers
    engine.dispose()


def test_ac001_user_model_column():
    from einstein_test.models.user import User
    from einstein_test.services.user import DEFAULT_USER_MODEL

    assert "model" in User.__table__.c, "User.model existe"
    assert User.__table__.c.model.nullable is True, "coluna nullable"
    assert DEFAULT_USER_MODEL == "azure/gpt-5-mini", "modelo padrão é o mini"


def test_ac001_userread_exposes_model():
    from einstein_test.schemas.user import UserRead

    assert "model" in UserRead.model_fields, "UserRead expõe model"


def test_ac003_allowed_models_default(monkeypatch):
    from einstein_test.services import rag as rag

    monkeypatch.delenv("ALLOWED_MODELS", raising=False)
    assert hasattr(rag, "allowed_models")
    models = rag.allowed_models()
    assert "azure/gpt-5-mini" in models
    assert "azure/gpt-6-luna" in models


def test_ac003_allowed_models_env_override(monkeypatch):
    from einstein_test.services import rag as rag

    monkeypatch.setenv("ALLOWED_MODELS", "azure/gpt-5-mini,azure/gpt-777")
    assert rag.allowed_models() == ["azure/gpt-5-mini", "azure/gpt-777"]


def test_ac002_get_me_returns_default_model(client):
    c, h = client
    r = c.get("/users/me", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert "model" in body
    assert body["model"] == "azure/gpt-5-mini", "usuário novo usa o modelo mini padrão"


def test_ac002_patch_me_valid(client):
    c, h = client
    r = c.patch("/users/me", json={"model": "azure/gpt-6-luna"}, headers=h)
    assert r.status_code == 200
    assert r.json()["model"] == "azure/gpt-6-luna"
    # GET reflete
    assert c.get("/users/me", headers=h).json()["model"] == "azure/gpt-6-luna"


def test_ac002_patch_me_invalid_422(client):
    c, h = client
    r = c.patch("/users/me", json={"model": "azure/gpt-inexistente"}, headers=h)
    assert r.status_code == 422, "modelo não permitido -> 422"
    assert "detail" in r.json()


def test_ac002_patch_me_null_restores_default(client):
    c, h = client
    c.patch("/users/me", json={"model": "azure/gpt-6-luna"}, headers=h)
    r = c.patch("/users/me", json={"model": None}, headers=h)
    assert r.status_code == 200
    assert r.json()["model"] == "azure/gpt-5-mini", "null restaura o modelo mini padrão"


def test_ac004_get_rag_service_uses_user_model(monkeypatch):
    from einstein_test.services import rag as rag

    monkeypatch.setenv("OPENAI_API_KEY", "sk-teste")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://spillway.ensinoeinstein.com/openai/v1")
    monkeypatch.setenv("ALLOWED_MODELS", "azure/gpt-5-mini,azure/gpt-6-luna")

    class _Repo:
        def search_similar(self, *a, **k):
            return []

    rag.reset_rag_factory()

    svc = rag.get_rag_service(_Repo(), model="azure/gpt-6-luna")
    assert isinstance(svc.llm, rag.ChatOpenAIAdapter)
    assert svc.llm.model == "azure/gpt-6-luna", "adapter com o model do usuário"

    svc2 = rag.get_rag_service(_Repo(), model="azure/gpt-5-mini")
    assert svc2.llm is not svc.llm, "adapter por usuário (não singleton LLM)"
    assert svc2.llm.model == "azure/gpt-5-mini"
    rag.reset_rag_factory()


def test_ac005_rag_endpoint_uses_user_model(monkeypatch, client):
    # integração: POST /messages passa o model do current_user ao get_rag_service
    from einstein_test.services import rag as rag
    from einstein_test.services.rag import FakeChatLLM, RagService, set_rag_factory
    from einstein_test.vector import FakeEmbedder

    captured = {}

    def _factory(*args, **kwargs):
        captured["model"] = kwargs.get("model")
        return RagService(
            llm=FakeChatLLM(),
            retriever=kwargs["retriever"],
            embedder=FakeEmbedder(),
        )

    set_rag_factory(_factory)
    c, h = client
    # define o modelo do usuário
    c.patch("/users/me", json={"model": "azure/gpt-6-luna"}, headers=h)
    chat = c.post("/chats", json={"name": "c"}, headers=h).json()
    resp = c.post(
        f"/chats/{chat['id']}/messages",
        json={"content": "oi"},
        headers={**h, "Accept": "text/event-stream"},
    )
    assert resp.status_code == 200
    assert captured.get("model") == "azure/gpt-6-luna", (
        "RAG recebeu o model do usuário"
    )
    rag.reset_rag_factory()


def test_call_time_model_outside_allowlist_uses_default(monkeypatch, client):
    # defense in depth: model armazenado fora da allowlist é tratado como
    # default (null) em call-time
    from einstein_test.services import rag as rag
    from einstein_test.services.rag import FakeChatLLM, RagService, set_rag_factory
    from einstein_test.vector import FakeEmbedder

    captured = {}

    def _factory(*args, **kwargs):
        captured["model"] = kwargs.get("model")
        return RagService(
            llm=FakeChatLLM(), retriever=kwargs["retriever"], embedder=FakeEmbedder()
        )

    set_rag_factory(_factory)
    c, h = client
    # força um model inválido direto no banco (simula env alterada depois)
    monkeypatch.setenv("ALLOWED_MODELS", "azure/gpt-5-mini")
    c.patch("/users/me", json={"model": "azure/gpt-5-mini"}, headers=h)
    # agora o usuário tem model armazenado = gpt-5-mini (ainda permitido)
    # simulamos a allowlist mudando para não incluir:
    monkeypatch.setenv("ALLOWED_MODELS", "azure/gpt-6-luna")
    chat = c.post("/chats", json={"name": "c"}, headers=h).json()
    from einstein_test.models.user import User
    from einstein_test.api.dependencies import _SessionLocal

    with _SessionLocal() as s:
        u = s.query(User).filter(User.email == "model@b.com").one()
        u.model = "azure/gpt-5-mini"  # deixa fora da allowlist agora
        s.commit()
    resp = c.post(
        f"/chats/{chat['id']}/messages",
        json={"content": "oi"},
        headers={**h, "Accept": "text/event-stream"},
    )
    assert resp.status_code == 200
    assert captured.get("model") == "azure/gpt-6-luna", (
        "model fora da allowlist cai para o primeiro modelo permitido"
    )
    rag.reset_rag_factory()


def test_ac002_patch_model_trimmed(client):
    c, h = client
    r = c.patch("/users/me", json={"model": "  azure/gpt-6-luna "}, headers=h)
    assert r.status_code == 200
    assert r.json()["model"] == "azure/gpt-6-luna", "payload com espaços normalizado"