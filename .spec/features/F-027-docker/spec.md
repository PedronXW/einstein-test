# F-027 — Dockerfile + compose com app e worker

## Resumo
Cria **imagem Docker** da aplicação (uv, non-root) e os serviços `api`
(FastAPI/uvicorn) e `worker` (Celery) no `docker-compose.yml`, conectados à
infra (postgres/minio/redis). `docker compose up` sobe a API de verdade —
antes o compose só tinha infra e a aplicação rodava via `uv run einstein-test`.

## Histórias de usuário
- U-001 — **Como** dev/operador, **quero** uma imagem Docker da aplicação,
  **para** rodar a API e o worker de forma reproduzível.
- U-002 — **Como** operador, **quero** `docker compose up` subir a API + worker
  + infra (postgres/minio/redis), **para** ambiente de produção/demo completo.
- U-003 — **Como** dev, **quero** que a imagem seja **non-root**, **para**
  segurança (menos privilégios no container).

## Critérios de aceite
> Critérios são registrados mecanicamente (AC-### → story → semântica técnica → dono T-###)
> — edite `criteria.reg` e reflita aqui por legibilidade ponto a ponto.

- AC-001 — [U-001] `Dockerfile` (base python 3.12-slim, instala uv, copia
  `pyproject.toml`/`uv.lock`, `uv sync --frozen --no-dev`, copia `src`, exec
  como **non-root** `uvicorn einstein_test.main:create_app --factory`).
- AC-002 — [U-002] `docker-compose.yml` ganha serviços `api` (build do
  Dockerfile, expõe 8000, depends_on postgres/minio/redis, env) e `worker`
  (mesma imagem, comando `celery -A einstein_test.tasks worker`); compose
  continua com a infra.
- AC-003 — [U-003] Imagem roda como usuário non-root (USER no Dockerfile);
  teste de estrutura verifica `USER` presente e `--factory` no entrypoint.
- AC-004 — [U-002] `docker compose config` é válido (parsável); teste confere
  a presença de `api`/`worker`/serviços de infra e envs-chave.

## Suposições (status: aberto|confirmada|rejeitada)
- A-001 — Dockerfile multi-stage/leve com uv + non-root. — confirmada
- A-002 — Compose com serviços api + worker + infra existente. — confirmada
- A-003 — Entrypoint uvicorn com `--factory` (fails-fast no startup). — confirmada

## Perguntas em aberto
- (nenhuma)