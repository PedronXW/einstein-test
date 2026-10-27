"""Endpoints REST de chat."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from einstein_test.api.dependencies import get_session
from einstein_test.repositories.sqlalchemy import ChatRepositorySQLAlchemy
from einstein_test.schemas.chat import ChatCreate, ChatRead
from einstein_test.services.chat import ChatNotFoundError, ChatService

router = APIRouter(prefix="/chats", tags=["chats"])


def _service(session: Session) -> ChatService:
    return ChatService(ChatRepositorySQLAlchemy(session))


@router.post("", response_model=ChatRead)
def create_chat(payload: ChatCreate, session: Session = Depends(get_session)) -> ChatRead:
    service = _service(session)
    chat = service.create_chat(name=payload.name, description=payload.description)
    return ChatRead.model_validate(chat)


@router.get("", response_model=list[ChatRead])
def list_chats(session: Session = Depends(get_session)) -> list[ChatRead]:
    service = _service(session)
    chats = service.list_chats()
    return [ChatRead.model_validate(c) for c in chats]


@router.get("/{chat_id}", response_model=ChatRead)
def get_chat(chat_id: int, session: Session = Depends(get_session)) -> ChatRead:
    service = _service(session)
    try:
        chat = service.get_chat(chat_id)
    except ChatNotFoundError:
        raise HTTPException(status_code=404, detail="chat não encontrado") from None
    return ChatRead.model_validate(chat)


@router.delete("/{chat_id}")
def delete_chat(chat_id: int, session: Session = Depends(get_session)) -> dict[str, str]:
    service = _service(session)
    try:
        service.delete_chat(chat_id)
    except ChatNotFoundError:
        raise HTTPException(status_code=404, detail="chat não encontrado") from None
    return {"status": "ok"}