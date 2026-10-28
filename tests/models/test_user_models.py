"""Testes TDD da feature F-012 (AC-001: model/repo User + bcrypt).

Valida o model User (email único, password_hash), o RepositoryUser e o hash
bcrypt (nunca senha em texto).
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from einstein_test.db.base import Base
from einstein_test.models import User
from einstein_test.repositories.user import UserRepositorySQLAlchemy
from einstein_test.security import hash_password, verify_password


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()


def test_ac001_user_model_registered():
    assert "users" in Base.metadata.tables, "tabela users registrada"


def test_ac001_user_columns():
    cols = {c.name for c in User.__table__.columns}
    assert {"id", "email", "password_hash"} <= cols
    assert "created_at" in cols, "timestamp mixin presente"


def test_ac001_user_email_unique():
    email_col = User.__table__.c.email
    assert email_col.unique is True, "email único enforçado"


def test_ac001_password_hash_never_plaintext():
    hashed = hash_password("segredo123")
    assert hashed != "segredo123", "hash nunca guarda a senha"
    assert verify_password("segredo123", hashed) is True
    assert verify_password("errada", hashed) is False


def test_ac001_bcrypt_hash_is_salted():
    h1 = hash_password("senha")
    h2 = hash_password("senha")
    assert h1 != h2, "bcrypt saltea o hash (mesmo password, hashes distintos)"


def test_ac001_repo_create_and_fetch_by_email(session):
    repo = UserRepositorySQLAlchemy(session)
    user = repo.create(email="a@b.com", password_hash=hash_password("123456"))
    assert user.id is not None
    assert user.email == "a@b.com"
    assert user.password_hash != "123456"

    found = repo.get_by_email("a@b.com")
    assert found is not None and found.id == user.id
    assert repo.get_by_email("nao@existe.com") is None


def test_ac001_repo_duplicate_email_raises(session):
    repo = UserRepositorySQLAlchemy(session)
    repo.create(email="dup@b.com", password_hash=hash_password("123456"))
    with pytest.raises(Exception):
        repo.create(email="dup@b.com", password_hash=hash_password("654321"))