# F-009 — Infra: remover minio-init + postgres vetorizado (pgvector)

## O que foi feito
Duas mudanças no `docker-compose.yml`:
1. **Removido o `minio-init`** (imagem `minio/mc`) — causava erro de pull
   (`pull access denied` no registry deste ambiente). O **MinIO
   (`minio/minio:latest`) é mantido** com mesmas portas/credenciais/volume/
   healthcheck; o bucket `einstein` agora se cria manualmente, ou
   automaticamente no startup da API via `MinioStorage.ensure_bucket`
   (cria se não existir, de forma idempotente).
2. **Postgres vetorizado**: `postgres:16-alpine` → **`ankane/pgvector:latest`**
   (PostgreSQL 15.4 + extensão `vector`), para embeddings futuros. O init do
   banco de teste (F-001) continua.

## Critérios de aceite implementados

| AC | História | Status | Prova |
|----|----------|--------|-------|
| AC-001 | U-001 — `minio` mantido + `minio-init` removido | PASS | `tests/infra/test_infra_docker.py -k ac001_no_minio` |
| AC-002 | U-001 — `docker compose config` válido; únicas imagens `ankane/pgvector` + `minio/minio` | PASS | `tests/infra/test_infra_docker.py -k ac002_imagens` / `docker compose config -q` |
| AC-003 | U-002 — `MinioStorage` mantém default `localhost:9000` | PASS | `tests/services/test_file_service.py -k ac003` |
| AC-004 | U-003 — `postgres` usa `ankane/pgvector:latest`; init de teste preservado | PASS | `tests/infra/test_infra_docker.py -k ac004_pgvector` |

## Veredito mecânico
`specs proof --strict F-009-fix-minio-image` → `PASS` (4/4 ACs).
`uv run pytest` → `96 passed`. `docker compose config -q` → exit 0.
Validação viva: postgres 15.4 com `CREATE EXTENSION vector` OK (dist
`[1,2,3] <-> [4,5,6] = 5.196`); `alembic upgrade head` cria chats/files/messages.

## Como usar (ou usar `uv build`/`uv run pytest`)
- `docker compose up -d` sobe postgres (pgvector) + minio.
- Banco de teste `einstein_test` criado pelo init (F-001) — preservado.
- Alembic: `uv run alembic upgrade head` aponta para o postgres vetorizado.

## Arquivos
- `docker-compose.yml` — removido `minio-init`; `postgres` → `ankane/pgvector:latest`
- `tests/infra/test_infra_docker.py`, `tests/alembic/test_alembic_config.py`,
  `tests/services/test_file_service.py` — testes evoluídos

## Notas
- **`ankane/pgvector:latest` é PostgreSQL 15.4** — se o volume `pgdata` foi
  inicializado com postgres 16, recrie com `docker compose down -v` (perde a
  data local).
- Bucket `einstein`: crie manualmente (console `:9001` ou cliente boto3 do host,
  ver `docs/features/F-001-infra-local.md`); o servidor MinIO não inclui `mc`.
- A doc da F-001 (minio-init + bucket no 1º boot) é superada pela F-009.