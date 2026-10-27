"""Testes TDD da feature F-016 (rate limiting).

Valida o RateLimiter (janela deslizante em memória, reset), o middleware
(429 + Retry-After, limites por rota incluindo POST /chats, exclusions) e a
identificação confiável (XFF só via proxy de confiança).
"""

import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from einstein_test.db.base import Base
from einstein_test.main import create_app
from einstein_test.middleware.rate_limit import RateLimiter
from tests.conftest import register_and_login


@pytest.fixture
def client(monkeypatch):
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
        yield c
    engine.dispose()


def test_ac004_limiter_tracks_requests():
    limiter = RateLimiter(limit=2, window=60)
    key = ("user@b.com", "/chats/1/messages")
    ok1, _ = limiter.allow(key)
    ok2, _ = limiter.allow(key)
    assert ok1 is True and ok2 is True
    ok, retry = limiter.allow(key)
    assert ok is False
    assert retry is not None and retry > 0, "Retry-After em segundos"


def test_ac004_sliding_window_expires():
    limiter = RateLimiter(limit=1, window=60)
    key = ("a", "/x")
    ok, _ = limiter.allow(key)
    assert ok is True
    limiter._entries[key] = [time.time() - 120]
    ok, _ = limiter.allow(key)
    assert ok is True, "requisições fora da janela expiradas"


def test_ac004_reset_clears():
    limiter = RateLimiter(limit=1, window=60)
    limiter.allow(("u", "/x"))
    RateLimiter.reset()
    ok, _ = limiter.allow(("u", "/x"))
    assert ok is True


def test_ac003_login_rate_limited(client):
    # login limitado a 10/min (default por env); 11º -> 429
    for i in range(10):
        r = client.post("/auth/login", json={"email": f"u{i}@b.com", "password": "x"})
        assert r.status_code in (200, 401), "antes do limite não 429"
    r = client.post("/auth/login", json={"email": "mais@b.com", "password": "x"})
    assert r.status_code == 429, "login excedido -> 429"
    assert "retry-after" in {k.lower() for k in r.headers}, "header Retry-After"


def test_ac003_messages_rate_limited(client, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_MESSAGES", "3")
    headers = register_and_login(client, email="rl@b.com")
    chat = client.post("/chats", json={"name": "c"}, headers=headers)
    assert chat.status_code in (200, 201)
    chat_id = chat.json()["id"]
    for i in range(3):
        r = client.post(
            f"/chats/{chat_id}/messages",
            json={"content": f"q{i}"},
            headers={**headers, "Accept": "text/event-stream"},
        )
        assert r.status_code == 200, "antes do limite não 429"
    r = client.post(
        f"/chats/{chat_id}/messages",
        json={"content": "q"},
        headers={**headers, "Accept": "text/event-stream"},
    )
    assert r.status_code == 429, "messages excedido -> 429"
    assert "retry-after" in {k.lower() for k in r.headers}


def test_ac002_chats_rate_limited(client, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_CHATS", "3")
    headers = register_and_login(client, email="rl_chats@b.com")
    for i in range(3):
        r = client.post("/chats", json={"name": f"c{i}"}, headers=headers)
        assert r.status_code in (200, 201)
    r = client.post("/chats", json={"name": "c4"}, headers=headers)
    assert r.status_code == 429, "POST /chats excedido -> 429"
    assert "retry-after" in {k.lower() for k in r.headers}


def test_ac005_docs_not_rate_limited(client):
    for _ in range(8):
        assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200


def test_ac005_authed_counts_by_user_not_ip(client):
    headers = register_and_login(client, email="rl2@b.com")
    for i in range(12):
        r = client.post("/chats", json={"name": f"c{i}"}, headers=headers)
        assert r.status_code in (200, 201)
    assert client.get("/chats", headers=headers).status_code == 200


def test_xff_not_trusted_by_default(client):
    # sem TRUSTED_PROXIES, o X-Forwarded-For forjado não é usado (mesmo IP)
    RateLimiter.reset()
    for i in range(10):
        r = client.post(
            "/auth/login",
            json={"email": f"sp{i}@b.com", "password": "x"},
            headers={"x-forwarded-for": f"1.2.3.{i}"},
        )
        assert r.status_code in (200, 401)
    r = client.post(
        "/auth/login",
        json={"email": "sp@b.com", "password": "x"},
        headers={"x-forwarded-for": "9.9.9.9"},
    )
    assert r.status_code == 429, "spoofing de XFF não burla o limite (IP real)"