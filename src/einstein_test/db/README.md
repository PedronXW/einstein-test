# db — infraestrutura de banco (engine)

Inicialização do SQLAlchemy, compartilhada pela API e pelo worker (sem
dependência da camada HTTP).

## Arquivos

- `engine.py` — `create_engine_from_config(url)`: engine único a partir das
  `Settings`, com pool configurável (`DATABASE_POOL_*`, F-014). Em SQLite omite
  parâmetros de pool não suportados.
- `base.py` — `Base` declarativa (base dos models).

## Nota

A **session factory** exposta ao HTTP vive em `api/dependencies.py`; o Celery
cria engine a partir daqui. As migrações ficam em `alembic/` (rodam no boot
com **advisory lock** para não ter corrida entre api e worker).
