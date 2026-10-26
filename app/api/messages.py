"""Endpoints REST de message."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_session
from app.repositories.chat import ChatRepositorySQLAlchemy
from app.repositories.message import MessageRepositorySQLAlchemy
from app.schemas.message import MessageCreate, MessageRead
from app.services.chat import ChatNotFoundError, ChatService
from app.services.message import MessageNotFoundError, MessageService

router = APIRouter(tags=["messages"])


def _chat_service(session: Session) -> ChatService:
    return ChatService(ChatRepositorySQLAlchemy(session))


def _message_service(session: Session) -> MessageService:
    return MessageService(MessageRepositorySQLAlchemy(session))


def _ensure_chat_exists(session: Session, chat_id: int) -> None:
    try:
        _chat_service(session).get_chat(chat_id)
    except ChatNotFoundError:
        raise HTTPException(status_code=404, detail="chat não encontrado") from None


@router.post("/chats/{chat_id}/messages", response_model=MessageRead)
def create_message(
    chat_id: int,
    payload: MessageCreate,
    session: Session = Depends(get_session),
) -> MessageRead:
    _ensure_chat_exists(session, chat_id)
    service = _message_service(session)
    message = service.create_message(
        chat_id=chat_id, content=payload.content, role=payload.role
    )
    return MessageRead.model_validate(message)


@router.get("/chats/{chat_id}/messages", response_model=list[MessageRead])
def list_messages(
    chat_id: int, session: Session = Depends(get_session)
) -> list[MessageRead]:
    _ensure_chat_exists(session, chat_id)
    service = _message_service(session)
    messages = service.list_messages(chat_id=chat_id)
    return [MessageRead.model_validate(m) for m in messages]


@router.get("/messages/{message_id}", response_model=MessageRead)
def get_message(
    message_id: int, session: Session = Depends(get_session)
) -> MessageRead:
    service = _message_service(session)
    try:
        message = service.get_message(message_id)
    except MessageNotFoundError:
        raise HTTPException(
            status_code=404, detail="message não encontrado"
        ) from None
    return MessageRead.model_validate(message)


@router.delete("/messages/{message_id}")
def delete_message(
    message_id: int, session: Session = Depends(get_session)
) -> dict[str, str]:
    service = _message_service(session)
    try:
        service.delete_message(message_id)
    except MessageNotFoundError:
        raise HTTPException(
            status_code=404, detail="message não encontrado"
        ) from None
    return {"status": "ok"}