"""Fixtures compartilhadas de testes."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from einstein_test.db.base import Base
from einstein_test.main import create_app


@pytest.fixture(autouse=True)
def _jwt_secret(monkeypatch):
    """Assegura JWT_SECRET configurado nos testes (token assinado local)."""
    monkeypatch.setenv("JWT_SECRET", "segredo-dos-testes-0123456789abcdefghijklmnop")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")


@pytest.fixture
def app_client():
    """Client do app com SQLite :memory: e headers de usuário autenticado."""
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
        headers = register_and_login(c, email="user@b.com")
        yield c, headers
    engine.dispose()


@pytest.fixture
def session_factory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    def _factory() -> Session:
        return Session(engine)

    yield _factory
    engine.dispose()


def register_and_login(client: TestClient, email: str, password: str = "senha123") -> dict:
    """Registra e autentica um usuário; retorna headers Authorization."""
    assert client.post(
        "/users", json={"email": email, "password": password}
    ).status_code in (201, 409)
    resp = client.post(
        "/auth/login", json={"email": email, "password": password}
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}