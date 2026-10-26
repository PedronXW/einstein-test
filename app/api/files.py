"""Endpoints REST de file."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.dependencies import get_session
from app.repositories.chat import ChatRepositorySQLAlchemy
from app.repositories.file import FileRepositorySQLAlchemy
from app.schemas.file import FileRead
from app.services.chat import ChatNotFoundError, ChatService
from app.services.file import FileNotFound, FileService

router = APIRouter(tags=["files"])

MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB


def _chat_service(session: Session) -> ChatService:
    return ChatService(ChatRepositorySQLAlchemy(session))


def _file_service(session: Session) -> FileService:
    return FileService(FileRepositorySQLAlchemy(session))


def _ensure_chat_exists(session: Session, chat_id: int) -> None:
    try:
        _chat_service(session).get_chat(chat_id)
    except ChatNotFoundError:
        raise HTTPException(status_code=404, detail="chat não encontrado") from None


@router.post("/chats/{chat_id}/files", response_model=FileRead)
async def upload_file(
    chat_id: int,
    file: UploadFile,
    session: Session = Depends(get_session),
) -> FileRead:
    _ensure_chat_exists(session, chat_id)
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="arquivo muito grande")
    service = _file_service(session)
    file_ = service.create_file(
        chat_id=chat_id,
        name=file.filename or "arquivo",
        content=content,
        content_type=file.content_type,
    )
    return FileRead.model_validate(file_)


@router.get("/chats/{chat_id}/files", response_model=list[FileRead])
def list_files(
    chat_id: int, session: Session = Depends(get_session)
) -> list[FileRead]:
    _ensure_chat_exists(session, chat_id)
    service = _file_service(session)
    files = service.list_files(chat_id=chat_id)
    return [FileRead.model_validate(f) for f in files]


@router.get("/files/{file_id}", response_model=FileRead)
def get_file(
    file_id: int, session: Session = Depends(get_session)
) -> FileRead:
    service = _file_service(session)
    try:
        file_ = service.get_file(file_id)
    except FileNotFound:
        raise HTTPException(status_code=404, detail="file não encontrado") from None
    return FileRead.model_validate(file_)


@router.delete("/files/{file_id}")
def delete_file(
    file_id: int, session: Session = Depends(get_session)
) -> dict[str, str]:
    service = _file_service(session)
    try:
        service.delete_file(file_id)
    except FileNotFound:
        raise HTTPException(status_code=404, detail="file não encontrado") from None
    return {"status": "ok"}