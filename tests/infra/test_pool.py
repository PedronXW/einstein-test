"""Testes TDD da feature F-014 (pool de conexões).

Valida a factory create_engine_from_config (parâmetros de pool via env com
defaults e override), o uso dela por get_session/configure_session_factory,
pool_pre_ping/pool_timeout e a concorrência com N sessões paralelas.
"""

import threading

import pytest
from sqlalchemy import text
from sqlalchemy.pool import QueuePool

from einstein_test.api import dependencies
from einstein_test.api.dependencies import (
    create_engine_from_config,
    get_session,
)
from einstein_test.settings import _build_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    """Limpa o cache do settings para os overrides de env valerem."""
    _build_settings.cache_clear()
    yield
    _build_settings.cache_clear()


def _postgres_url() -> str:
    return "postgresql://einstein:einstein@localhost:5432/einstein"


def test_ac001_factory_defaults(monkeypatch):
    monkeypatch.delenv("DATABASE_POOL_SIZE", raising=False)
    monkeypatch.delenv("DATABASE_MAX_OVERFLOW", raising=False)
    monkeypatch.delenv("DATABASE_POOL_TIMEOUT", raising=False)
    # sqlite é funcional
    engine = create_engine_from_config("sqlite:///:memory:")
    try:
        assert engine.pool is not None
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    finally:
        engine.dispose()
    # postgres aplica defaults 10/20/30
    engine = create_engine_from_config(_postgres_url())
    try:
        assert isinstance(engine.pool, QueuePool)
        assert engine.pool._pool.maxsize == dependencies.DEFAULT_POOL_SIZE
        assert engine.pool._max_overflow == dependencies.DEFAULT_MAX_OVERFLOW
        assert engine.pool._timeout == float(dependencies.DEFAULT_POOL_TIMEOUT)
    finally:
        engine.dispose()


def test_ac001_factory_env_override(monkeypatch):
    # valores distintos dos defaults provam override via env
    monkeypatch.setenv("DATABASE_POOL_SIZE", "3")
    monkeypatch.setenv("DATABASE_MAX_OVERFLOW", "7")
    monkeypatch.setenv("DATABASE_POOL_TIMEOUT", "5")
    engine = create_engine_from_config(_postgres_url())
    try:
        assert engine.pool._pool.maxsize == 3, "DATABASE_POOL_SIZE aplicado"
        assert engine.pool._max_overflow == 7, "DATABASE_MAX_OVERFLOW aplicado"
        assert engine.pool._timeout == 5.0, "DATABASE_POOL_TIMEOUT aplicado"
    finally:
        engine.dispose()


def test_ac001_get_session_uses_factory(monkeypatch):
    from einstein_test.db.base import Base

    engine = create_engine_from_config("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    dependencies.configure_session_factory(engine)

    gen = get_session()
    session = next(gen)
    try:
        result = session.execute(text("SELECT 1"))
        assert result.scalar() == 1
    finally:
        session.close()
        gen.close()
    engine.dispose()


def test_ac002_configure_accepts_url():
    dependencies.configure_session_factory("sqlite:///:memory:")
    gen = get_session()
    session = next(gen)
    try:
        assert session is not None
        session.execute(text("SELECT 1"))
    finally:
        session.close()
        gen.close()


def test_ac003_pool_pre_ping_and_timeout(monkeypatch):
    monkeypatch.setenv("DATABASE_POOL_TIMEOUT", "12")
    engine = create_engine_from_config(_postgres_url())
    try:
        assert engine.pool._pre_ping is True, "pool_pre_ping habilitado"
        assert engine.pool._timeout == 12.0, "pool_timeout aplicado"
    finally:
        engine.dispose()


def test_ac004_concurrency_20_sessions():
    import tempfile
    from pathlib import Path

    from sqlalchemy import create_engine as _create_engine
    from sqlalchemy.pool import QueuePool as _QP

    tmp = Path(tempfile.mkstemp(suffix=".db")[1])
    try:
        # SQLite com arquivo e QueuePool compartilhado: threads concorrentes
        # usam o mesmo pool (não SingletonThreadPool por-thread)
        engine = _create_engine(f"sqlite:///{tmp}", poolclass=_QP)
        errors: list[Exception] = []

        def _worker(n: int) -> None:
            from sqlalchemy.orm import Session

            try:
                with Session(engine) as session:
                    session.execute(text(f"SELECT {n}"))
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=_worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"erros nas threads: {errors}"
    finally:
        engine.dispose()
        tmp.unlink(missing_ok=True)


def test_get_session_lazy_with_env_url(monkeypatch):
    # get_session sem configure_session_factory usa DATABASE_URL via factory
    from einstein_test.db.base import Base

    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    dependencies._SessionLocal = None  # reset global para forçar caminho lazy
    try:
        gen = get_session()
        session = next(gen)
        try:
            Base.metadata.create_all(session.get_bind())
            assert session.execute(text("SELECT 1")).scalar() == 1
        finally:
            session.close()
            gen.close()
    finally:
        dependencies._SessionLocal = None