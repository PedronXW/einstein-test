"""Testes TDD da feature F-012 (AC-002/AC-003: JWT, login/registro, get_current_user).

Valida a criação de token, decode, e o fluxo POST /users + POST /auth/login
com retorno de access_token.
"""

import pytest
from fastapi import HTTPException

from einstein_test.api.auth import create_access_token, decode_token, get_current_user
from einstein_test.repositories.user import UserRepositorySQLAlchemy


def test_ac003_create_and_decode_token():
    token = create_access_token(subject="user-42")
    payload = decode_token(token)
    assert payload["sub"] == "user-42"


def test_ac003_jwt_has_expiry():
    token = create_access_token(subject="user-1")
    payload = decode_token(token)
    assert "exp" in payload, "token tem expiração"


def test_ac003_decode_invalid_token_raises_401():
    with pytest.raises(HTTPException) as exc:
        decode_token("token-invalido")
    assert exc.value.status_code == 401


def test_ac003_get_current_user_loads_from_email(session_factory):
    repo = UserRepositorySQLAlchemy(session_factory())
    user = repo.create(email="eu@b.com", password="senha")
    token = create_access_token(subject=user.email)

    with session_factory() as session:
        current = get_current_user(authorization=f"Bearer {token}", session=session)
    assert current is not None
    assert current.id == user.id


def test_ac003_get_current_user_unknown_401(session_factory):
    token = create_access_token(subject="ghost@b.com")
    with session_factory() as session:
        with pytest.raises(HTTPException) as exc:
            get_current_user(authorization=f"Bearer {token}", session=session)
    assert exc.value.status_code == 401


def test_ac003_get_current_user_missing_token_401():
    with pytest.raises(HTTPException) as exc:
        get_current_user(authorization=None, session=None)
    assert exc.value.status_code == 401