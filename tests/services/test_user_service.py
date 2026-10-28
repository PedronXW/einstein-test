"""Testes TDD da feature F-031 (AC-001: UserService no lugar de repo direto no controller).

Valida que o acesso a dados de User passa pelo service, com a regra de modelo
(allowlist + default) encapsulada no service.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from einstein_test.db.base import Base
from einstein_test.models import User
from einstein_test.services.user import DEFAULT_USER_MODEL, UserService


@pytest.fixture
def repo_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()


@pytest.fixture
def service(repo_session):
    from einstein_test.repositories.user import UserRepositorySQLAlchemy

    return UserService(UserRepositorySQLAlchemy(repo_session))


def test_ac001_default_model_lives_in_service():
    assert DEFAULT_USER_MODEL == "azure/gpt-5-mini", "constante exposta pelo service"


def test_ac001_get_by_email_returns_user(service, repo_session):
    from einstein_test.security import hash_password

    repo_user = User(email="eu@b.com", password_hash=hash_password("senha"))
    repo_session.add(repo_user)
    repo_session.flush()
    found = service.get_by_email("eu@b.com")
    assert found is not None and found.email == "eu@b.com"


def test_ac001_set_model_valid(service, repo_session, monkeypatch):
    monkeypatch.setenv("ALLOWED_MODELS", "azure/gpt-5-mini,azure/gpt-6-luna")
    user = User(email="a@b.com", password_hash="x")
    repo_session.add(user)
    repo_session.flush()
    service.set_model(user, "azure/gpt-6-luna")
    assert user.model == "azure/gpt-6-luna"


def test_ac001_set_model_invalid_raises(service, repo_session, monkeypatch):
    monkeypatch.setenv("ALLOWED_MODELS", "azure/gpt-5-mini")
    user = User(email="a@b.com", password_hash="x")
    repo_session.add(user)
    repo_session.flush()
    with pytest.raises(ValueError):
        service.set_model(user, "azure/gpt-inexistente")


def test_ac001_set_model_none_restores_default(service, repo_session, monkeypatch):
    monkeypatch.setenv("ALLOWED_MODELS", "azure/gpt-5-mini,azure/gpt-6-luna")
    user = User(email="a@b.com", password_hash="x")
    repo_session.add(user)
    repo_session.flush()
    service.set_model(user, None)
    assert user.model == DEFAULT_USER_MODEL


def test_ac001_resolve_model_valid(service, repo_session, monkeypatch):
    monkeypatch.setenv("ALLOWED_MODELS", "azure/gpt-5-mini,azure/gpt-6-luna")
    user = User(email="a@b.com", password_hash="x", model="azure/gpt-6-luna")
    repo_session.add(user)
    repo_session.flush()
    assert service.resolve_model(user) == "azure/gpt-6-luna"


def test_ac001_resolve_model_outside_allowlist_uses_first(service, repo_session, monkeypatch):
    monkeypatch.setenv("ALLOWED_MODELS", "azure/gpt-5-mini,azure/gpt-6-luna")
    user = User(email="a@b.com", password_hash="x", model="azure/gpt-fora")
    repo_session.add(user)
    repo_session.flush()
    assert service.resolve_model(user) == "azure/gpt-5-mini", (
        "modelo fora da allowlist cai para o primeiro permitido"
    )


def test_ac001_resolve_model_none_uses_first(service, repo_session, monkeypatch):
    monkeypatch.setenv("ALLOWED_MODELS", "azure/gpt-5-mini,azure/gpt-6-luna")
    user = User(email="a@b.com", password_hash="x", model=None)
    repo_session.add(user)
    repo_session.flush()
    assert service.resolve_model(user) == "azure/gpt-5-mini"
