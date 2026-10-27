"""Testes TDD da feature F-002 (FastAPI hello world).

Valida AC-001/AC-002: app FastAPI com GET / retornando hello world.
"""

import pytest
from fastapi.testclient import TestClient

from einstein_test.main import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_ac001_get_root_returns_200(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200


def test_ac002_get_root_returns_hello_json(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.json() == {"message": "Hello World"}
    assert resp.headers["content-type"] == "application/json"