"""Testes TDD da feature F-031 (AC-002: security module separado do repository).

Valida que hash/verify bcrypt vivem em `einstein_test.security` e que o
`UserRepositorySQLAlchemy` persiste o hash pronto (não sabe que bcrypt existe).
"""

import inspect

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from einstein_test.db.base import Base
from einstein_test.repositories.user import UserRepositorySQLAlchemy
from einstein_test.security import hash_password, verify_password


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()


def test_ac002_security_hashes_and_verifies():
    hashed = hash_password("segredo123")
    assert hashed != "segredo123"
    assert verify_password("segredo123", hashed) is True
    assert verify_password("errada", hashed) is False


def test_ac002_security_hash_is_salted():
    assert hash_password("senha") != hash_password("senha")


def test_ac002_repo_does_not_import_bcrypt():
    import einstein_test.repositories.user as repo_module

    # o módulo não define hash/verify (vieram do security)
    assert not hasattr(repo_module, "hash_password")
    assert not hasattr(repo_module, "verify_password")
    assert "import bcrypt" not in inspect.getsource(repo_module), (
        "repo não importa bcrypt"
    )


def test_ac002_repo_create_persists_hash_ready(session):
    repo = UserRepositorySQLAlchemy(session)
    user = repo.create(email="a@b.com", password_hash=hash_password("123456"))
    assert user.id is not None
    assert user.password_hash != "123456"
    assert verify_password("123456", user.password_hash) is True
