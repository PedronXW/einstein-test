# F-027 — Dockerfile + compose com app e worker

## O que foi feito
Criada **imagem Docker** da aplicação e os serviços `api` + `worker` no
`docker-compose.yml` — agora `docker compose up` sobe a API de verdade (antes
só a infra: postgres/minio/redis).

- **`Dockerfile`**: python 3.12-slim + uv (`uv sync --frozen --no-dev`), copia
  `src`, executa como **non-root** (`useradd` + `USER appuser`), entrypoint
  `uvicorn einstein_test.main:create_app --factory` (mantém o fails-fast).
- **`docker-compose.yml`**: serviços `api` (build, porta 8000, healthcheck
  `/health`, `depends_on` infra saudável) e `worker` (mesma imagem, `celery -A
  einstein_test.tasks worker`), com envs via `.env` (`JWT_SECRET`,
  `OPENAI_API_KEY` obrigatórios com `:?`).

## Critérios de aceite implementados

| AC | História | Status | Prova |
|----|----------|--------|-------|
| AC-001 | U-001 — Dockerfile (uv --frozen --no-dev, 3.12, `--factory`) | PASS | `tests/infra/test_docker.py -k ac001` |
| AC-002 | U-002 — compose com api + worker + infra | PASS | `tests/infra/test_docker.py -k ac002` |
| AC-003 | U-003 — imagem non-root (USER no Dockerfile) | PASS | `tests/infra/test_docker.py -k ac003` |
| AC-004 | U-002 — `docker compose config` válido (parsável) | PASS | `tests/infra/test_docker.py -k ac004` |

## Veredito mecânico
`specs proof --strict F-027-docker` → `PASS` (4/4 ACs). `uv run pytest` →
`317 passed, 1 deselected`. `ruff check .` → all passed.

## Como rodar
```bash
docker compose up --build   # sobe postgres+minio+redis+api+worker
curl http://localhost:8000/health   # → {"status":"ok"}
```
Requer `.env` com `JWT_SECRET` e `OPENAI_API_KEY` (o compose falha rápido sem eles).

## Arquivos
- `Dockerfile` (novo)
- `docker-compose.yml` (+`api`, `worker`)
- `tests/infra/test_docker.py` (novo), `tests/infra/test_infra_docker.py`
  (ajustado: service_block por indent 2, imagens/build)

## Notas
- O `service_block` do teste passou a exigir indent 2 (top-level) para não
  confundir com o `depends_on.minio/postgres` aninhado do compose config.
- `api`/`worker` usam `build: .` (sem `image:` explícita) — o compose gera o
  nome automaticamente; testes verificam `build`/`dockerfile`.