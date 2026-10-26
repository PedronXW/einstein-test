# F-002 — FastAPI hello + Alembic configurado

## Resumo
Adicionar ao projeto uma aplicação FastAPI **idiomática** (pacote `app/` com
routers separados) expondo um endpoint hello world em `GET /`, rodável via
**uvicorn**, e configurar o **Alembic** apontando para o PostgreSQL do docker
compose — porém ainda **sem gerar/rodar migrations**.

## Histórias de usuário
- U-001 — **Como** dev, **quero** um app FastAPI com `GET /` retornando hello
  world, **para** ter uma API mínima rodando.
- U-002 — **Como** dev, **quero** subir o servidor com uvicorn, **para** testar
  o endpoint localmente na hora.
- U-003 — **Como** dev, **quero** o Alembic configurado apontando para o postgres
  do compose (com base SQLAlchemy), **para** preparar migrações futuras — sem
  ainda criar executar migration alguma.

## Critérios de aceite
> Critérios são registrados mecanicamente (AC-### → story → semântica técnica → dono T-###)
> — edite `criteria.reg` e reflita aqui por legibilidade ponto a ponto.

- AC-001 — [U-001] Pacote `app/` com `create_app()` em `app/main.py` que inclui
  o router de `app/api/`; `GET /` responde `200` com corpo `{"message": "Hello World"}`.
- AC-002 — [U-001] Teste com `TestClient` valida `GET /` → `200` e exatamente o JSON acima.
- AC-003 — [U-002] Dependências `fastapi`, `uvicorn` (e `httpx` p/ TestClient)
  presentes no `pyproject.toml`; comandos de teste rodam com uv.
- AC-004 — [U-003] `alembic.ini` + `alembic/` presentes; `env.py` lê
  `DATABASE_URL` do ambiente com default `postgresql://einstein:einstein@localhost:5432/einstein`
  (postgres do compose) e define `target_metadata = Base.metadata`.
- AC-005 — [U-003] Base declarativa SQLAlchemy existe (ex.: `app/db/base.py` com
  `Base = declarative_base()`), referenciada pelo Alembic; **nenhuma** migration
  gerada (diretório `alembic/versions/` vazio).

## Suposições (status: aberto|confirmada|rejeitada)
- A-001 — Estrutura `app/` na raiz com routers separados (escolha do usuário). — confirmada
- A-002 — Endpoint hello em `GET /` com resposta `{"message": "Hello World"}`. — confirmada
- A-003 — Uvicorn incluído como dependência e runner local. — confirmada
- A-004 — Alembic aponta para o postgres do docker compose via `DATABASE_URL`. — confirmada
- A-005 — Base declarativa SQLAlchemy incluída (sem models, sem migrations). — confirmada

## Perguntas em aberto
- (nenhuma)