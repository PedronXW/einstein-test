"""Aplicação FastAPI."""

from fastapi import FastAPI

from app.api.chats import router as chats_router
from app.api.files import router as files_router
from app.api.messages import router as messages_router
from app.api.router import router


def create_app() -> FastAPI:
    app = FastAPI(title="einstein-test")
    app.include_router(router)
    app.include_router(chats_router)
    app.include_router(messages_router)
    app.include_router(files_router)
    return app


app = create_app()