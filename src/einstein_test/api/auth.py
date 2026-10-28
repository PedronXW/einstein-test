"""Autenticação JWT e dependências de usuário autenticado.

- `create_access_token(subject)` -> string JWT (pyjwt) com `sub` e `exp`
  (helpers JWT moram em `einstein_test.security`; reutilizados aqui).
- `decode_token(token)` -> payload (raise 401 se inválido/expirado).
- `get_current_user(authorization, session)` -> User ou 401.

Configuração via ambiente (testes/injeção) ou `.env`: `JWT_SECRET`
(obrigatório), `ACCESS_TOKEN_EXPIRE_MINUTES` (default 60). O secret é
resolvido uma única vez e cacheado.
"""

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from einstein_test.api.dependencies import get_session
from einstein_test.models import User
from einstein_test.repositories.user import UserRepositorySQLAlchemy
from einstein_test.security import create_access_token, decode_token
from einstein_test.services.user import UserService

__all__ = [
    "create_access_token",
    "decode_token",
    "get_current_user",
]


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
    user = UserService(UserRepositorySQLAlchemy(session)).get_by_email(email)
    if user is None:
        raise HTTPException(status_code=401, detail="usuário não encontrado")
    return user