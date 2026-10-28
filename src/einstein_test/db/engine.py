"""Engine do SQLAlchemy a partir da configuração (infra de banco).

Moradia única do factory de engine — usada por `api/dependencies` (HTTP) e por
`tasks` (Celery) sem depender da camada de API.
"""

from sqlalchemy import Engine, create_engine, make_url

from einstein_test.settings import get_settings


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


__all__ = ["create_engine_from_config"]
