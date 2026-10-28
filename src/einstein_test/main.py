"""Aplicação FastAPI."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from uvicorn import run as uvicorn_run

from einstein_test.api.auth_router import router as auth_router
from einstein_test.api.chats import router as chats_router
from einstein_test.api.files import router as files_router
from einstein_test.api.messages import router as messages_router
from einstein_test.api.router import router
from einstein_test.logging_setup import configure_logging
from einstein_test.middleware.logging_middleware import RequestIdMiddleware
from einstein_test.middleware.rate_limit import RateLimitMiddleware
from einstein_test.settings import validate_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup: garante o bucket do storage (cria se não existir)."""
    from einstein_test.storage import get_storage

    get_storage().ensure_bucket()
    yield


def create_app() -> FastAPI:
    validate_settings()  # fails fast: config obrigatória ausente/inválida
    configure_logging()
    app = FastAPI(title="einstein-test", lifespan=lifespan)
    # ordem: RequestId externo (captura 429 do rate limit e 500), depois rate limit
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.include_router(router)
    app.include_router(auth_router)
    app.include_router(chats_router)
    app.include_router(messages_router)
    app.include_router(files_router)
    return app


def main(argv: list[str] | None = None) -> None:
    """Entrypoint CLI: `einstein-test` levanta uvicorn (com a factory).

    Usa `factory=True` + string importável (necessário para `reload`/`workers`)
    e roda o fails-fast do `validate_settings` no startup do worker.

    Opções: `--workers N` (multi-processo; reload desativado quando >1).
    """
    import argparse

    parser = argparse.ArgumentParser(prog="einstein-test")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--workers", type=int, default=1, help="número de workers")
    parser.add_argument("--reload", action="store_true", help="auto-reload (dev)")
    args = parser.parse_args(argv)

    uvicorn_run(
        "einstein_test.main:create_app",
        host=args.host,
        port=args.port,
        workers=args.workers,
        reload=args.reload and args.workers == 1,
        factory=True,
    )