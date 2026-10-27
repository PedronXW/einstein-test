"""Dependency de sessão do SQLAlchemy (uma por request)."""

import os
from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

DEFAULT_DATABASE_URL = "postgresql://einstein:einstein@localhost:5432/einstein"

_SessionLocal: sessionmaker | None = None


def configure_session_factory(engine: Engine) -> None:
    """Define o sessionmaker global (usado pelos testes com SQLite :memory:)."""
    global _SessionLocal
    _SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """Cria uma Session por request; encerra ao final."""
    global _SessionLocal
    if _SessionLocal is None:
        url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
        configure_session_factory(create_engine(url, pool_pre_ping=True))
    if _SessionLocal is None:
        raise RuntimeError("session factory não configurada")
    session = _SessionLocal()
    try:
        yield session
    finally:
        session.close()