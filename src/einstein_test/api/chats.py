"""Endpoints REST de chat (protegidos por autenticação)."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from einstein_test.api.auth import get_current_user
from einstein_test.api.dependencies import get_session
from einstein_test.models import User
from einstein_test.repositories.sqlalchemy import ChatRepositorySQLAlchemy
from einstein_test.schemas.chat import ChatCreate, ChatRead
from einstein_test.schemas.page import Page
from einstein_test.services.chat import ChatNotFoundError, ChatService
from einstein_test.services.pagination import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE,
    MAX_PAGE_SIZE,
    MIN_PAGE,
)

router = APIRouter(prefix="/chats", tags=["chats"])


def _service(session: Session) -> ChatService:
    return ChatService(ChatRepositorySQLAlchemy(session))


@router.post("", response_model=ChatRead, status_code=201)
def create_chat(
    payload: ChatCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ChatRead:
    service = _service(session)
    chat = service.create_chat(
        user_id=current_user.id,
        name=payload.name,
        description=payload.description,
    )
    return ChatRead.model_validate(chat)


@router.get("", response_model=Page[ChatRead])
def list_chats(
    page: int = Query(MIN_PAGE, ge=MIN_PAGE, le=MAX_PAGE),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=MIN_PAGE, le=MAX_PAGE_SIZE),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Page[ChatRead]:
    service = _service(session)
    items, total = service.list_chats_page(
        user_id=current_user.id, page=page, page_size=page_size
    )
    return Page[ChatRead].build(
        items=[ChatRead.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{chat_id}", response_model=ChatRead)
def get_chat(
    chat_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ChatRead:
    service = _service(session)
    try:
        chat = service.get_chat(chat_id, user_id=current_user.id)
    except ChatNotFoundError:
        raise HTTPException(status_code=404, detail="chat não encontrado") from None
    return ChatRead.model_validate(chat)


@router.delete("/{chat_id}")
def delete_chat(
    chat_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    service = _service(session)
    try:
        service.delete_chat(chat_id, user_id=current_user.id)
    except ChatNotFoundError:
        raise HTTPException(status_code=404, detail="chat não encontrado") from None
    return {"status": "ok"}