import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool, text

from alembic import context

from einstein_test.db.base import Base
from einstein_test.models import Chat, File, FileChunk, Message, User  # noqa: F401

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# URL do postgres do docker compose por default; sobrescrevível via ambiente.
config.set_main_option(
    "sqlalchemy.url",
    os.getenv(
        "DATABASE_URL",
        "postgresql://einstein:einstein@localhost:5432/einstein",
    ),
)

# add your model's MetaData object here for 'autogenerate' support.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    Serializa migrações entre processos (api/worker/replicas) via advisory
    lock do Postgres — evita corrida de `upgrade head` simultâneos no boot.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        if connection.dialect.name == "postgresql":
            # Adquire o advisory lock em AUTOCOMMIT para NÃO abrir transação
            # antes do alembic: se o lock dispara o autobegin do SQLAlchemy,
            # o `context.begin_transaction()` do alembic vira no-op e todo o
            # DDL é rolado de volta quando a conexão fecha (banco fica vazio).
            lock_conn = connection.execution_options(isolation_level="AUTOCOMMIT")
            lock_conn.execute(text("SELECT pg_advisory_lock(hashtext('einstein_alembic'))"))
            try:
                _run(connection)
            finally:
                lock_conn.execute(text("SELECT pg_advisory_unlock(hashtext('einstein_alembic'))"))
        else:
            _run(connection)


def _run(connection) -> None:
    context.configure(
        connection=connection, target_metadata=target_metadata
    )

    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
