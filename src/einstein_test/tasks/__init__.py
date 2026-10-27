"""Aplicação Celery e tasks de background (F-015).

- `celery_app`: app Celery com broker/backend Redis (config via env).
- `vectorize_file(file_id)`: baixa o conteúdo do storage, vetoriza
  (extrai→chunk→embed→insert) e atualiza o File (status ready/error).
"""

import os

from celery import Celery

from einstein_test.logging_setup import get_logger
from einstein_test.models import File  # noqa: F401
from einstein_test.models.file import FILE_STATUS_ERROR, FILE_STATUS_PENDING, FILE_STATUS_READY

logger = get_logger("tasks")

celery_app = Celery(
    "einstein_test.tasks",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
)
celery_app.conf.task_track_started = True
celery_app.conf.broker_connection_retry_on_startup = True


def _url_object_key(url: str) -> tuple[str, str] | None:
    """Converte `s3://<bucket>/<key>` em (bucket, key); None se inválido."""
    if not url or not url.startswith("s3://"):
        return None
    parts = url.split("/", 3)
    if len(parts) < 4:
        return None
    return parts[2], parts[3]


@celery_app.task(name="einstein_test.tasks.vectorize_file")
def vectorize_file(file_id: int) -> dict:
    """Vetoriza o arquivo em background e atualiza seu status."""
    from einstein_test.api.dependencies import create_engine_from_config
    from einstein_test.repositories import (
        FileRepositorySQLAlchemy,
        VectorRepositorySQLAlchemy,
    )
    from einstein_test.services.file import FileService
    from einstein_test.storage import get_storage
    from einstein_test.vector import get_embedder

    engine = create_engine_from_config()
    try:
        from sqlalchemy.orm import Session

        with Session(bind=engine) as session:
            file_repo = FileRepositorySQLAlchemy(session)
            file_ = file_repo.get_by_id(file_id)
            if file_ is None:
                return {"file_id": file_id, "status": "missing"}
            if file_.status == FILE_STATUS_READY:
                return {"file_id": file_id, "status": FILE_STATUS_READY}

            storage = get_storage()
            loc = _url_object_key(file_.url)
            if loc is None:
                file_.status = FILE_STATUS_ERROR
                file_.error_detail = "url inválida do arquivo"
                session.commit()
                return {"file_id": file_id, "status": FILE_STATUS_ERROR}
            bucket, key = loc
            content = storage.download(bucket, key)

            service = FileService(
                file_repo,
                storage=storage,
                vector_repository=VectorRepositorySQLAlchemy(session),
                embedder=get_embedder(),
            )
            chunk_ids, reference = service._vectorize(
                file_.id, file_.name, content
            )
            file_.chunk_ids = chunk_ids
            file_.vector_reference = reference
            file_.status = FILE_STATUS_READY
            file_.error_detail = None
            session.commit()
            return {
                "file_id": file_id,
                "status": FILE_STATUS_READY,
                "chunks": len(chunk_ids),
            }
    except Exception as exc:  # noqa: BLE001
        logger.warning("vetorização falhou", extra={
            "event": "vectorize_failed", "file_id": file_id,
            "error": type(exc).__name__,
        })
        try:
            from sqlalchemy.orm import Session

            with Session(bind=engine) as session:
                file_ = session.get(File, file_id)
                if file_ is not None and file_.status != FILE_STATUS_READY:
                    file_.status = FILE_STATUS_ERROR
                    file_.error_detail = str(exc.__class__.__name__)
                    session.commit()
        except Exception as inner:  # noqa: BLE001
            logger.error("falha ao marcar erro", extra={
                "event": "vectorize_mark_error_failed", "file_id": file_id,
                "error": type(inner).__name__,
            })
            if file_ is not None and file_.status != FILE_STATUS_READY:
                pass
        return {"file_id": file_id, "status": FILE_STATUS_ERROR}
    finally:
        engine.dispose()