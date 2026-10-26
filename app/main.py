"""Aplicação FastAPI."""

from fastapi import FastAPI

from app.api.chats import router as chats_router
from app.api.router import router


def create_app() -> FastAPI:
    app = FastAPI(title="einstein-test")
    app.include_router(router)
    app.include_router(chats_router)
    return app


app = create_app()