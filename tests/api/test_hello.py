"""Testes da API: healthcheck.

Valida GET /health: retorna 200 com status ok e valida o banco (sessão).
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from einstein_test.db.base import Base
from einstein_test.main import create_app


@pytest.fixture
def client() -> TestClient:
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
    c = TestClient(app)
    yield c
    engine.dispose()


def test_health_returns_ok(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    assert resp.headers["content-type"] == "application/json"