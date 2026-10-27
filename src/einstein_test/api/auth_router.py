"""Endpoints de auth: POST /users, POST /auth/login, GET/PATCH /users/me."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from einstein_test.api.auth import create_access_token, get_current_user
from einstein_test.api.dependencies import get_session
from einstein_test.models import User
from einstein_test.models.user import DEFAULT_USER_MODEL
from einstein_test.schemas.user import TokenRead, UserCreate, UserLogin, UserRead
from einstein_test.services.auth import (
    AuthService,
    EmailAlreadyRegistered,
    InvalidCredentials,
)
from einstein_test.services.rag import allowed_models

router = APIRouter(tags=["auth"])


class UserModelUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str | None = Field(default=None, max_length=127)


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


@router.get("/users/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(current_user)


@router.patch("/users/me", response_model=UserRead)
def update_me(
    payload: UserModelUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> UserRead:
    model = payload.model.strip() if payload.model else DEFAULT_USER_MODEL
    if model not in allowed_models():
        raise HTTPException(
            status_code=422, detail="modelo não suportado"
        )
    current_user.model = model
    # UoW (F-018): `get_session` commita ao final do request
    session.flush()
    return UserRead.model_validate(current_user)