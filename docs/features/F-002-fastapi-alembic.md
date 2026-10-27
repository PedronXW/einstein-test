# F-002 — FastAPI hello + Alembic configurado

## O que foi feito
Aplicação FastAPI idiomática (pacote `app/` com routers separados) expondo
`GET /` → `{"message": "Hello World"}`, runner via **uvicorn**, e Alembic
configurado apontando para o PostgreSQL do docker compose — sem nenhuma
migration gerada/executada ainda.

## Critérios de aceite implementados

| AC | História | Status | Prova |
|----|----------|--------|-------|
| AC-001 | U-001 — `app/` com `create_app()` + router; `GET /` 200 | PASS | `tests/api/test_hello.py::test_ac001_get_root_returns_200` |
| AC-002 | U-001 — corpo exato `{"message": "Hello World"}` | PASS | `tests/api/test_hello.py::test_ac002_get_root_returns_hello_json` |
| AC-003 | U-002 — deps `fastapi`, `uvicorn`, `httpx`, `sqlalchemy`, `alembic`, `psycopg` | PASS | `tests/alembic/test_alembic_config.py::test_ac003_deps_in_pyproject` |
| AC-004 | U-003 — `alembic.ini` + `env.py` com `DATABASE_URL` (default do compose) e `target_metadata = Base.metadata`; prova executa `env.py` offline | PASS | `tests/alembic/test_alembic_config.py::test_ac004_*` |
| AC-005 | U-003 — `app/db/base.py` com `Base` declarativa; `versions/` vazio (`.gitkeep` commitado) | PASS | `tests/alembic/test_alembic_config.py::test_ac005_*` |

## Veredito mecânico
`specs proof --strict F-002-fastapi-alembic` → `PASS` (5/5 ACs). `specs gate` → `PASS`.
Validação viva: `uvicorn einstein_test.main:app` → `GET /` `200` `{"message":"Hello World"}`;
`alembic check` com postgres do compose → `No new upgrade operations detected` (exit 0).

## Como usar
```sh
uv run uvicorn einstein_test.main:app --reload   # sobe a API em http://127.0.0.1:8000
docker compose up -d postgres          # postgres para o Alembic
uv run alembic current                 # conecta e mostra revisão atual (nenhuma ainda)
export DATABASE_URL="postgresql://einstein:einstein@localhost:5432/einstein"
uv run alembic revision --autogenerate -m "inicial"   # (futuro)
```

## Arquivos principais
- `app/main.py` — `create_app()` + instância `app`
- `app/api/router.py` — router com `GET /`
- `app/db/base.py` — `Base = declarative_base()`
- `alembic.ini`, `alembic/env.py` — config Alembic (default → postgres do compose)
- `tests/api/`, `tests/alembic/` — provas dos critérios

## Notas
- A-004 confirmada: Alembic aponta para `postgresql://einstein:einstein@localhost:5432/einstein`
  (postgres do compose) via `DATABASE_URL`, sobrescrevível por ambiente.
- Driver `psycopg[binary]` incluído para o Alembic operar online com o postgres.