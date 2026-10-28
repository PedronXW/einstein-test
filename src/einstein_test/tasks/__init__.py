"""Aplicação Celery e tasks de background (F-015/F-020).

- `celery_app`: app Celery com broker/backend Redis (config via env).
- `vectorize_file(file_id)`: invoca `FileService.vectorize_uploaded` (a
  orquestração mora no service) com **retry (backoff exponencial)** para falhas
  transientes e `error` imediato para erros permanentes.
"""

import os
from contextlib import contextmanager

from celery import Celery

from einstein_test.logging_setup import get_logger
from einstein_test.services.file import (
    FILE_STATUS_ERROR,
    FILE_STATUS_READY,
    FileService,
    VectorizationError,
)

logger = get_logger("tasks")

celery_app = Celery(
    "einstein_test.tasks",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
)
celery_app.conf.task_track_started = True
celery_app.conf.broker_connection_retry_on_startup = True

VECTORIZE_MAX_RETRIES = int(os.getenv("VECTORIZE_MAX_RETRIES", "3"))
VECTORIZE_RETRY_BACKOFF = int(os.getenv("VECTORIZE_RETRY_BACKOFF", "2"))


# Exceções consideradas permanentes (não re-tentáveis): rede/validação do
# payload, invariantes, etc. — qualquer outra exceção é tratada como
# transiente (storage/LLM/DB temporário) e dispara retry.
class PermanentVectorizationError(Exception):
    """Erro não re-tentável no processamento do arquivo."""


@contextmanager
def _service_scope(engine):
    """Abre uma Session e monta o FileService; fecha a sessão ao sair."""
    from sqlalchemy.orm import Session

    from einstein_test.repositories.file import FileRepositorySQLAlchemy
    from einstein_test.vector import VectorRepositorySQLAlchemy, get_embedder

    session = Session(bind=engine)
    try:
        yield FileService(
            FileRepositorySQLAlchemy(session),
            vector_repository=VectorRepositorySQLAlchemy(session),
            embedder=get_embedder(),
        )
    finally:
        session.close()


def _safe_mark_error(service: FileService, file_id: int, error: str) -> None:
    """Marca error sem deixar uma falha de persistência derrubar a task."""
    try:
        service.mark_error(file_id, error)
    except Exception as inner:  # noqa: BLE001
        logger.error("falha ao marcar erro", extra={
            "event": "vectorize_mark_error_failed", "file_id": file_id,
            "error": type(inner).__name__,
        })


@celery_app.task(bind=True, name="einstein_test.tasks.vectorize_file")
def vectorize_file(self, file_id: int) -> dict:
    """Vetoriza o arquivo em background e atualiza seu status.

    - Erro permanente (`VectorizationError`, url inválida, arquivo ausente):
      marca `error` imediatamente, sem retry.
    - Erro transiente (conexão/storage/LLM timeout): re-tenta com backoff
      exponencial até `VECTORIZE_MAX_RETRIES`; após esgotar, marca `error`.
    - Idempotente: arquivo `ready` não é reprocessado.
    """
    from einstein_test.db.engine import create_engine_from_config

    engine = create_engine_from_config()
    try:
        with _service_scope(engine) as service:
            status = service.vectorize_uploaded(file_id)
            chunks = 0
            if status == FILE_STATUS_READY:
                chunks = len(service.get_file(file_id).chunk_ids)
        logger.info("vetorização concluída", extra={
            "event": "vectorize_done", "file_id": file_id,
            "status": status, "chunks": chunks,
        })
        return {"file_id": file_id, "status": status, "chunks": chunks}
    except VectorizationError as exc:
        # erro permanente (invariants/dimensão/limite) — sem retry
        with _service_scope(engine) as service:
            _safe_mark_error(service, file_id, type(exc).__name__)
        return {"file_id": file_id, "status": FILE_STATUS_ERROR}
    except Exception as exc:  # noqa: BLE001 - transiente: retry com backoff
        logger.warning("vetorização falhou (tentativa %s)", self.request.retries + 1, extra={
            "event": "vectorize_failed", "file_id": file_id,
            "error": type(exc).__name__, "attempt": self.request.retries + 1,
        })
        if self.request.retries < VECTORIZE_MAX_RETRIES:
            delay = VECTORIZE_RETRY_BACKOFF * (2 ** self.request.retries)
            raise self.retry(exc=exc, countdown=delay)
        with _service_scope(engine) as service:
            _safe_mark_error(service, file_id, type(exc).__name__)
        return {"file_id": file_id, "status": FILE_STATUS_ERROR}
    finally:
        engine.dispose()
