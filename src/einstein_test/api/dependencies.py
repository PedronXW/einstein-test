"""Dependency de sessão do SQLAlchemy (uma por request)."""

import os
import threading
from collections.abc import Iterator

from sqlalchemy import Engine, create_engine, make_url
from sqlalchemy.orm import Session, sessionmaker

DEFAULT_DATABASE_URL = "postgresql://einstein:einstein@localhost:5432/einstein"
DEFAULT_POOL_SIZE = 10
DEFAULT_MAX_OVERFLOW = 20
DEFAULT_POOL_TIMEOUT = 30

ENV_POOL_SIZE = "DATABASE_POOL_SIZE"
ENV_MAX_OVERFLOW = "DATABASE_MAX_OVERFLOW"
ENV_POOL_TIMEOUT = "DATABASE_POOL_TIMEOUT"

_SessionLocal: sessionmaker | None = None
_lock = threading.Lock()


def _parse_int(name: str, default: int, minimum: int) -> int:
    try:
        return max(minimum, int(os.getenv(name, default)))
    except (TypeError, ValueError):
        return default


def create_engine_from_config(url: str | None = None) -> Engine:
    """Cria o engine a partir de env vars (pool configurável).

    No Postgres (QueuePool) aplica pool_size/max_overflow/pool_timeout. Em
    SQLite, esses parâmetros são omitidos (dialect usa SingletonThreadPool/
    StaticPool, que não os aceita).
    """
    url = url or os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    if make_url(url).get_backend_name() == "sqlite":
        return create_engine(url, pool_pre_ping=True)
    pool_size = _parse_int(ENV_POOL_SIZE, DEFAULT_POOL_SIZE, minimum=1)
    max_overflow = _parse_int(ENV_MAX_OVERFLOW, DEFAULT_MAX_OVERFLOW, minimum=0)
    pool_timeout = max(1.0, float(os.getenv(ENV_POOL_TIMEOUT, DEFAULT_POOL_TIMEOUT)))
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
    )


def configure_session_factory(bind: Engine | str) -> None:
    """Define o sessionmaker global a partir de um engine ou url."""
    global _SessionLocal
    if isinstance(bind, str):
        bind = create_engine_from_config(bind)
    with _lock:
        _SessionLocal = sessionmaker(bind=bind, autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """Cria uma Session por request; encerra ao final."""
    global _SessionLocal
    if _SessionLocal is None:
        with _lock:
            if _SessionLocal is None:
                _SessionLocal = sessionmaker(
                    bind=create_engine_from_config(),
                    autoflush=False,
                    expire_on_commit=False,
                )
    assert _SessionLocal is not None
    session = _SessionLocal()
    try:
        yield session
    finally:
        session.close()