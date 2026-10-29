"""Endpoints REST de message."""

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from einstein_test.api.auth import get_current_user
from einstein_test.api.dependencies import get_session
from einstein_test.logging_setup import current_request_id, get_logger
from einstein_test.models import User
from einstein_test.repositories.chat import ChatRepositorySQLAlchemy
from einstein_test.repositories.file import FileRepositorySQLAlchemy
from einstein_test.repositories.message import MessageRepositorySQLAlchemy
from einstein_test.repositories.user import UserRepositorySQLAlchemy
from einstein_test.schemas.message import MessageCreate, MessageRead
from einstein_test.schemas.page import Page
from einstein_test.services.chat import ChatNotFoundError, ChatService
from einstein_test.services.file import FileService
from einstein_test.services.message import (
    MAX_HISTORY,
    MessageNotFoundError,
    MessageService,
)
from einstein_test.services.pagination import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE,
    MAX_PAGE_SIZE,
    MIN_PAGE,
)
from einstein_test.services.rag import RagService, get_rag_service
from einstein_test.services.user import UserService
from einstein_test.vector import VectorRepositorySQLAlchemy

logger = get_logger("api.messages")

router = APIRouter(tags=["messages"])


def _chat_service(session: Session) -> ChatService:
    return ChatService(ChatRepositorySQLAlchemy(session))


def _message_service(session: Session) -> MessageService:
    return MessageService(MessageRepositorySQLAlchemy(session))


def _file_service(session: Session) -> FileService:
    return FileService(FileRepositorySQLAlchemy(session))


def _rag_service(session: Session, model: str | None = None) -> RagService:
    return get_rag_service(VectorRepositorySQLAlchemy(session), model=model)


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
    request_id = current_request_id()
    user_model = UserService(UserRepositorySQLAlchemy(session)).resolve_model(current_user)
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

    async def _file_readiness() -> object:
        return await run_in_threadpool(_file_service(session).rag_readiness, chat_id)

    readiness = await _file_readiness()
    processing = readiness.processing
    failed = readiness.failed

    async def _history() -> list[str]:
        def _load() -> list[str]:
            return [
                m.content
                for m in message_service.list_messages(chat_id=chat_id)
                if m.id != user_message.id
            ][-MAX_HISTORY:]

        return await run_in_threadpool(_load)

    def _notice() -> str:
        if readiness.code == "no_ready_files":
            return _sse_event(
                {
                    "code": "no_ready_files",
                    "message": "nenhum arquivo pronto para responder — envie arquivos",
                },
                event="notice",
            )
        if readiness.code == "partial_files":
            return _sse_event(
                {
                    "code": "partial_files",
                    "message": "resposta baseada apenas nos arquivos prontos",
                    "processing": processing,
                    "failed": failed,
                },
                event="notice",
            )
        return ""

    async def _stream() -> AsyncIterator[str]:
        if not readiness.can_answer:
            # AC-001: sem arquivos prontos -> notice SSE, sem LLM, sem assistant
            yield _notice()
            logger.info("mensagem sem arquivos prontos", extra={
                "event": "no_ready_files", "chat_id": chat_id,
                "message_id": user_message.id, "request_id": request_id,
            })
            return
        collected: list[str] = []
        try:
            history = await _history()
            notice = _notice()
            if notice:
                logger.info("aviso de arquivos parciais", extra={
                    "event": "partial_files_notice", "chat_id": chat_id,
                    "processing": processing, "failed": failed,
                    "request_id": request_id,
                })
                yield notice
            rag = await run_in_threadpool(_rag_service, session, user_model)
            n_tokens = 0
            async for token in rag.astream(
                question=user_message.content,
                chat_id=chat_id,
                history=history,
            ):
                collected.append(token)
                n_tokens += 1
                yield _sse_event(token)
            answer = "".join(collected)
            assistant = await run_in_threadpool(
                message_service.create_message,
                chat_id=chat_id,
                content=answer,
                role="assistant",
            )
            logger.info("RAG concluído", extra={
                "event": "rag_done", "chat_id": chat_id,
                "message_id": assistant.id, "n_tokens": n_tokens,
                "request_id": request_id,
            })
            yield _sse_event({"message_id": assistant.id})
            yield _sse_event("[DONE]")
        except Exception as exc:
            # evita gravar conteúdo do prompt/dados dos arquivos nos logs
            logger.error("falha no RAG", extra={
                "event": "rag_error", "chat_id": chat_id,
                "error": type(exc).__name__,
                "request_id": request_id,
            })
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


@router.get("/chats/{chat_id}/messages", response_model=Page[MessageRead])
def list_messages(
    chat_id: int,
    page: int = Query(MIN_PAGE, ge=MIN_PAGE, le=MAX_PAGE),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=MIN_PAGE, le=MAX_PAGE_SIZE),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Page[MessageRead]:
    try:
        _ensure_chat_owned(session, chat_id, current_user.id)
    except ChatNotFoundError:
        raise HTTPException(status_code=404, detail="chat não encontrado") from None
    service = _message_service(session)
    items, total = service.list_messages_page(chat_id=chat_id, page=page, page_size=page_size)
    return Page[MessageRead].build(
        items=[MessageRead.model_validate(m) for m in items],
        total=total,
        page=page,
        page_size=page_size,
    )


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