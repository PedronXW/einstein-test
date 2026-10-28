"""Autenticação JWT e dependências de usuário autenticado.

- `create_access_token(subject)` -> string JWT (pyjwt) com `sub` e `exp`.
- `decode_token(token)` -> payload (raise 401 se inválido/expirado).
- `get_current_user(authorization, session)` -> User ou 401.

Configuração via ambiente (testes/injeção) ou `.env`: `JWT_SECRET`
(obrigatório), `ACCESS_TOKEN_EXPIRE_MINUTES` (default 60). O secret é
resolvido uma única vez e cacheado.
"""

from datetime import UTC, datetime, timedelta
from functools import lru_cache

import jwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from einstein_test.api.dependencies import get_session
from einstein_test.models import User
from einstein_test.repositories.user import UserRepositorySQLAlchemy
from einstein_test.settings import get_settings

ALGORITHM = "HS256"
DEFAULT_EXPIRE_MINUTES = 60


@lru_cache(maxsize=1)
def _secret() -> str:
    secret = get_settings().jwt_secret
    if not secret:
        raise RuntimeError("JWT_SECRET não configurado (defina no .env)")
    return secret


@lru_cache(maxsize=1)
def _expire_minutes() -> int:
    return get_settings().access_token_expire_minutes


def create_access_token(subject: str) -> str:
    """Gera JWT com `sub` = email do usuário e expiração configurada."""
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=_expire_minutes()),
    }
    return jwt.encode(payload, _secret(), algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decodifica e valida o JWT; levanta 401 se inválido/expirado."""
    try:
        return jwt.decode(token, _secret(), algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="token inválido ou expirado") from None


def get_current_user(
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_session),
) -> User:
    """Resolve o usuário a partir do header `Authorization: Bearer <token>`."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="autenticação requerida"
        )
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="token inválido")
    payload = decode_token(token)
    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=401, detail="token inválido")
    user = UserRepositorySQLAlchemy(session).get_by_email(email.strip().lower())
    if user is None:
        raise HTTPException(status_code=401, detail="usuário não encontrado")
    return user