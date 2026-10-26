"""Aplicação FastAPI — hello world."""

from fastapi import FastAPI

from app.api.router import router


def create_app() -> FastAPI:
    app = FastAPI(title="einstein-test")
    app.include_router(router)
    return app


app = create_app()