"""Endpoints REST de file."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from einstein_test.api.auth import get_current_user
from einstein_test.api.dependencies import get_session
from einstein_test.logging_setup import get_logger
from einstein_test.models import User
from einstein_test.repositories.chat import ChatRepositorySQLAlchemy
from einstein_test.repositories.file import FileRepositorySQLAlchemy
from einstein_test.schemas.file import FileBatchFailure, FileBatchResult, FileRead
from einstein_test.services.chat import ChatNotFoundError, ChatService
from einstein_test.services.file import (
    MAX_UPLOAD_SIZE,
    BatchFileInput,
    DuplicateFileError,
    EmptyFileError,
    FileNotFound,
    FileService,
    FileTooLargeError,
    UnsupportedFileTypeError,
)

logger = get_logger("api.files")

router = APIRouter(tags=["files"])


def _chat_service(session: Session) -> ChatService:
    return ChatService(ChatRepositorySQLAlchemy(session))


def _file_service(session: Session) -> FileService:
    return FileService(
        FileRepositorySQLAlchemy(session),
        vector_repository=None,  # vetorização agora roda em background (F-015)
    )


def enqueue_vectorization(file_id: int) -> None:
    """Enfileira a tarefa de vetorização no Celery (mockável nos testes).

    Se o broker estiver indisponível, apenas registra no log — o upload já
    retornou 202 com status=pending; uma re-dispatch manual pode reenfileirar.
    """
    try:
        from einstein_test.tasks import vectorize_file

        vectorize_file.delay(file_id)
        logger.info("vetorização enfileirada", extra={
            "event": "vectorize_enqueue", "file_id": file_id, "status": "queued",
        })
    except Exception:  # noqa: BLE001
        logger.warning("falha ao enfileirar vetorização", extra={
            "event": "vectorize_enqueue_failed", "file_id": file_id,
        })


def _ensure_chat_owned(session: Session, chat_id: int, user_id: int) -> None:
    _chat_service(session).get_chat(chat_id, user_id=user_id)


@router.post("/chats/{chat_id}/files", response_model=FileRead, status_code=202)
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
    name = file.filename or "arquivo"
    content_type = file.content_type
    service = _file_service(session)

    def _create() -> FileRead:
        file_ = service.create_file(
            chat_id=chat_id,
            name=name,
            content=content,
            content_type=content_type,
        )
        return FileRead.model_validate(file_)

    try:
        created = await run_in_threadpool(_create)
    except FileTooLargeError:
        raise HTTPException(status_code=413, detail="arquivo muito grande") from None
    except EmptyFileError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except UnsupportedFileTypeError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from None
    except DuplicateFileError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    # vetorização em background
    await run_in_threadpool(enqueue_vectorization, created.id)
    return created


@router.post(
    "/chats/{chat_id}/files/batch",
    response_model=FileBatchResult,
    status_code=207,
)
async def upload_files_batch(
    chat_id: int,
    files: list[UploadFile] = File(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> FileBatchResult:
    try:
        _ensure_chat_owned(session, chat_id, current_user.id)
    except ChatNotFoundError:
        raise HTTPException(status_code=404, detail="chat não encontrado") from None
    service = _file_service(session)
    uploads = [
        BatchFileInput(
            name=f.filename or "arquivo",
            content=await f.read(MAX_UPLOAD_SIZE + 1),
            content_type=f.content_type,
        )
        for f in files
    ]
    try:
        result = await run_in_threadpool(service.create_files_batch, chat_id, uploads)
    except ValueError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from None
    for file_ in result.created:
        await run_in_threadpool(enqueue_vectorization, file_.id)
    return FileBatchResult(
        created=[FileRead.model_validate(f) for f in result.created],
        failures=[
            FileBatchFailure(index=fr.index, name=fr.name, reason=fr.reason)
            for fr in result.failures
        ],
    )


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
    from einstein_test.vector import VectorRepositorySQLAlchemy as _V

    service = FileService(
        FileRepositorySQLAlchemy(session),
        vector_repository=_V(session),
    )
    try:
        file_ = service.get_file(file_id)
        _ensure_chat_owned(session, file_.chat_id, current_user.id)
        service.delete_file(file_id)
    except (FileNotFound, ChatNotFoundError):
        raise HTTPException(status_code=404, detail="file não encontrado") from None
    return {"status": "ok"}