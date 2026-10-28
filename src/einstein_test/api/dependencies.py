"""Dependency de sessão do SQLAlchemy (uma por request)."""

import threading
from collections.abc import Iterator

from sqlalchemy import Engine, create_engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from einstein_test.settings import get_settings

DEFAULT_DATABASE_URL = "postgresql://einstein:einstein@localhost:5432/einstein"
DEFAULT_POOL_SIZE = 10
DEFAULT_MAX_OVERFLOW = 20
DEFAULT_POOL_TIMEOUT = 30

_SessionLocal: sessionmaker | None = None
_lock = threading.Lock()


def create_engine_from_config(url: str | None = None) -> Engine:
    """Cria o engine a partir de Settings (pool configurável).

    No Postgres (QueuePool) aplica pool_size/max_overflow/pool_timeout. Em
    SQLite, esses parâmetros são omitidos (dialect usa SingletonThreadPool/
    StaticPool, que não os aceita).
    """
    cfg = get_settings()
    url = url or cfg.database_url
    if make_url(url).get_backend_name() == "sqlite":
        return create_engine(url, pool_pre_ping=True)
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=cfg.database_pool_size,
        max_overflow=cfg.database_max_overflow,
        pool_timeout=cfg.database_pool_timeout,
    )


def configure_session_factory(bind: Engine | str) -> None:
    """Define o sessionmaker global a partir de um engine ou url."""
    global _SessionLocal
    if isinstance(bind, str):
        bind = create_engine_from_config(bind)
    with _lock:
        _SessionLocal = sessionmaker(bind=bind, autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """Cria uma Session por request; commit no fim e rollback em erro (UoW)."""
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
    except Exception:
        session.rollback()
        raise
    else:
        session.commit()
    finally:
        session.close()