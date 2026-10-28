"""Aplicação FastAPI."""

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


def create_app() -> FastAPI:
    validate_settings()  # fails fast: config obrigatória ausente/inválida
    configure_logging()
    app = FastAPI(title="einstein-test")
    # ordem: RequestId externo (captura 429 do rate limit e 500), depois rate limit
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.include_router(router)
    app.include_router(auth_router)
    app.include_router(chats_router)
    app.include_router(messages_router)
    app.include_router(files_router)
    return app


def main() -> None:
    """Entrypoint CLI: `einstein-test` levanta uvicorn con la app."""
    app = create_app()
    uvicorn_run(app, host="0.0.0.0", port=8000, reload=True)