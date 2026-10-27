"""Endpoints REST de file."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from einstein_test.api.auth import get_current_user
from einstein_test.api.dependencies import get_session
from einstein_test.models import User
from einstein_test.repositories.chat import ChatRepositorySQLAlchemy
from einstein_test.repositories.file import FileRepositorySQLAlchemy
from einstein_test.schemas.file import FileRead
from einstein_test.services.chat import ChatNotFoundError, ChatService
from einstein_test.services.file import FileNotFound, FileService, VectorizationError
from einstein_test.vector import VectorRepositorySQLAlchemy

router = APIRouter(tags=["files"])

MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB


def _chat_service(session: Session) -> ChatService:
    return ChatService(ChatRepositorySQLAlchemy(session))


def _file_service(session: Session) -> FileService:
    return FileService(
        FileRepositorySQLAlchemy(session),
        vector_repository=VectorRepositorySQLAlchemy(session),
    )


def _ensure_chat_owned(session: Session, chat_id: int, user_id: int) -> None:
    _chat_service(session).get_chat(chat_id, user_id=user_id)


@router.post("/chats/{chat_id}/files", response_model=FileRead)
async def upload_file(
    chat_id: int,
    file: UploadFile,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> FileRead:
    try:
        _ensure_chat_owned(session, chat_id, current_user.id)
    except ChatNotFoundError:
        raise HTTPException(status_code=404, detail="chat não encontrado") from None
    content = await file.read(MAX_UPLOAD_SIZE + 1)
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="arquivo muito grande")
    name = file.filename or "arquivo"
    content_type = file.content_type
    service = _file_service(session)

    def _create() -> FileRead:
        try:
            file_ = service.create_file(
                chat_id=chat_id,
                name=name,
                content=content,
                content_type=content_type,
            )
        except VectorizationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        return FileRead.model_validate(file_)

    return await run_in_threadpool(_create)


@router.get("/chats/{chat_id}/files", response_model=list[FileRead])
def list_files(
    chat_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[FileRead]:
    try:
        _ensure_chat_owned(session, chat_id, current_user.id)
    except ChatNotFoundError:
        raise HTTPException(status_code=404, detail="chat não encontrado") from None
    service = _file_service(session)
    files = service.list_files(chat_id=chat_id)
    return [FileRead.model_validate(f) for f in files]


@router.get("/files/{file_id}", response_model=FileRead)
def get_file(
    file_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> FileRead:
    service = _file_service(session)
    try:
        file_ = service.get_file(file_id)
        _ensure_chat_owned(session, file_.chat_id, current_user.id)
    except (FileNotFound, ChatNotFoundError):
        raise HTTPException(status_code=404, detail="file não encontrado") from None
    return FileRead.model_validate(file_)


@router.delete("/files/{file_id}")
def delete_file(
    file_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    service = _file_service(session)
    try:
        file_ = service.get_file(file_id)
        _ensure_chat_owned(session, file_.chat_id, current_user.id)
        service.delete_file(file_id)
    except (FileNotFound, ChatNotFoundError):
        raise HTTPException(status_code=404, detail="file não encontrado") from None
    return {"status": "ok"}