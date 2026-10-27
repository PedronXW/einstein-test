"""Endpoints REST de message."""

import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from einstein_test.api.auth import get_current_user
from einstein_test.api.dependencies import get_session
from einstein_test.models import User
from einstein_test.repositories import VectorRepositorySQLAlchemy
from einstein_test.repositories.chat import ChatRepositorySQLAlchemy
from einstein_test.repositories.message import MessageRepositorySQLAlchemy
from einstein_test.schemas.message import MessageCreate, MessageRead
from einstein_test.services.chat import ChatNotFoundError, ChatService
from einstein_test.services.message import MessageNotFoundError, MessageService
from einstein_test.services.rag import RagService, get_rag_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["messages"])

MAX_HISTORY = 10


def _chat_service(session: Session) -> ChatService:
    return ChatService(ChatRepositorySQLAlchemy(session))


def _message_service(session: Session) -> MessageService:
    return MessageService(MessageRepositorySQLAlchemy(session))


def _rag_service(session: Session) -> RagService:
    return get_rag_service(VectorRepositorySQLAlchemy(session))


def _ensure_chat_owned(session: Session, chat_id: int, user_id: int) -> None:
    _chat_service(session).get_chat(chat_id, user_id=user_id)


def _sse_event(data: str, *, event: str | None = None) -> str:
    """Formata um evento SSE (dados JSON-encoded; linhas normalizadas)."""
    encoded = json.dumps(data, ensure_ascii=False)
    if event:
        return f"event: {event}\ndata: {encoded}\n\n"
    return f"data: {encoded}\n\n"


@router.post("/chats/{chat_id}/messages")
async def create_message(
    chat_id: int,
    payload: MessageCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    try:
        await run_in_threadpool(_ensure_chat_owned, session, chat_id, current_user.id)
    except ChatNotFoundError:
        raise HTTPException(status_code=404, detail="chat não encontrado") from None
    message_service = _message_service(session)

    async def _setup() -> object:
        return await run_in_threadpool(
            message_service.create_message,
            chat_id=chat_id,
            content=payload.content,
            role="user",
        )

    user_message = await _setup()

    async def _history() -> list[str]:
        def _load() -> list[str]:
            return [
                m.content
                for m in message_service.list_messages(chat_id=chat_id)
                if m.id != user_message.id
            ][-MAX_HISTORY:]

        return await run_in_threadpool(_load)

    async def _stream() -> AsyncIterator[str]:
        collected: list[str] = []
        try:
            history = await _history()
            rag = await run_in_threadpool(_rag_service, session)
            async for token in rag.astream(
                question=user_message.content,
                chat_id=chat_id,
                history=history,
            ):
                collected.append(token)
                yield _sse_event(token)
            answer = "".join(collected)
            assistant = await run_in_threadpool(
                message_service.create_message,
                chat_id=chat_id,
                content=answer,
                role="assistant",
            )
            yield _sse_event({"message_id": assistant.id})
            yield _sse_event("[DONE]")
        except Exception as exc:
            # evita gravar conteúdo do prompt/dados dos arquivos nos logs
            logger.error("falha no RAG (chat=%s): %s", chat_id, type(exc).__name__)
            yield _sse_event(
                {"error": "falha ao gerar resposta"},
                event="error",
            )

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/chats/{chat_id}/messages", response_model=list[MessageRead])
def list_messages(
    chat_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[MessageRead]:
    try:
        _ensure_chat_owned(session, chat_id, current_user.id)
    except ChatNotFoundError:
        raise HTTPException(status_code=404, detail="chat não encontrado") from None
    service = _message_service(session)
    messages = service.list_messages(chat_id=chat_id)
    return [MessageRead.model_validate(m) for m in messages]


@router.get("/messages/{message_id}", response_model=MessageRead)
def get_message(
    message_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> MessageRead:
    service = _message_service(session)
    try:
        message = service.get_message(message_id)
        _ensure_chat_owned(session, message.chat_id, current_user.id)
    except (MessageNotFoundError, ChatNotFoundError):
        raise HTTPException(
            status_code=404, detail="message não encontrado"
        ) from None
    return MessageRead.model_validate(message)


@router.delete("/messages/{message_id}")
def delete_message(
    message_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    service = _message_service(session)
    try:
        message = service.get_message(message_id)
        _ensure_chat_owned(session, message.chat_id, current_user.id)
        service.delete_message(message_id)
    except (MessageNotFoundError, ChatNotFoundError):
        raise HTTPException(
            status_code=404, detail="message não encontrado"
        ) from None
    return {"status": "ok"}