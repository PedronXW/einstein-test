"""Segurança: hash/verify de senha (bcrypt) e helpers JWT.

Política criptográfica e de assinatura de token isolada da persistência — o
repository persiste o hash já pronto e o middleware/controllers importam os
helpers JWT daqui, nunca da camada `api` (regra de ouro controller→service→
repository→model; infra não depende de api).
"""

from datetime import UTC, datetime, timedelta
from functools import lru_cache

import bcrypt
import jwt
from fastapi import HTTPException

from einstein_test.settings import get_settings

ALGORITHM = "HS256"
DEFAULT_EXPIRE_MINUTES = 60


def hash_password(password: str) -> str:
    """Hash bcrypt da senha (salteado)."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verifica senha contra o hash bcrypt."""
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"), password_hash.encode("utf-8")
        )
    except ValueError:
        return False


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


__all__ = [
    "ALGORITHM",
    "DEFAULT_EXPIRE_MINUTES",
    "create_access_token",
    "decode_token",
    "hash_password",
    "verify_password",
]
