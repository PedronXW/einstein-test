"""Endpoints de auth: POST /users e POST /auth/login."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from einstein_test.api.auth import create_access_token
from einstein_test.api.dependencies import get_session
from einstein_test.schemas.user import TokenRead, UserCreate, UserLogin, UserRead
from einstein_test.services.auth import (
    AuthService,
    EmailAlreadyRegistered,
    InvalidCredentials,
)

router = APIRouter(tags=["auth"])


def _service(session: Session) -> AuthService:
    return AuthService.with_session(session)


@router.post("/users", response_model=UserRead, status_code=201)
def register(
    payload: UserCreate, session: Session = Depends(get_session)
) -> UserRead:
    service = _service(session)
    try:
        user = service.register(email=payload.email, password=payload.password)
    except EmailAlreadyRegistered:
        raise HTTPException(
            status_code=409, detail="email já cadastrado"
        ) from None
    return UserRead.model_validate(user)


@router.post("/auth/login", response_model=TokenRead)
def login(payload: UserLogin, session: Session = Depends(get_session)) -> TokenRead:
    service = _service(session)
    try:
        user = service.authenticate(email=payload.email, password=payload.password)
    except InvalidCredentials:
        raise HTTPException(
            status_code=401, detail="usuário ou senha inválidos"
        ) from None
    token = create_access_token(subject=user.email)
    return TokenRead(access_token=token, token_type="bearer")