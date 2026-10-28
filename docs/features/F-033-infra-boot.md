# F-033 — Boot automático de infra: bucket MinIO + migrations alembic

## O que foi feito
Automatização do boot de infra + correções de compose + doc do Insomnia pendente.

### Bucket do MinIO criado no startup (U-001)
- `MinioStorage.ensure_bucket(name)` verifica `head_bucket` e cria o bucket
  (`create_bucket`) se ausente — **idempotente**.
- Erro "bucket não existe" (404/`NoSuchBucket`) → cria; conflito de criação
  por corrida (`BucketAlreadyOwnedByYou`/409) é tratado como sucesso — outro
  worker/replica já criou.
- Erros de autenticação/5xx do cliente S3 propagam; **indisponibilidade do MinIO
  no boot** (erro de conexão, no head ou no create) apenas loga e segue.
- `InMemoryStorage.ensure_bucket` é um **no-op** (mantém o Protocol `Storage`).
- `create_app` usa **lifespan** que chama `get_storage().ensure_bucket()`.
- Fixture autouse `_storage_fake` no conftest usa `InMemoryStorage` — testes não
  tocam MinIO real no startup.

### Migrations alembic no boot (U-002)
- `docker/entrypoint.sh`: roda `.venv/bin/alembic upgrade head` antes do comando
  real (`exec "$@"`), com **retry configurável** (`MIGRATE_MAX_RETRIES`=10,
  `MIGRATE_RETRY_DELAY`=2s) e **exit 1** ao esgotar tentativas.
- `Dockerfile`: copia `alembic.ini`, `alembic/` e o entrypoint para a imagem;
  define `ENTRYPOINT` — vale para `api` **e** `worker`.
- `alembic/env.py` serializa migrações entre processos api/worker/replicas via
  **advisory lock do Postgres** (`pg_advisory_lock`) — evita corrida de DDL na
  primeira subida.

### Correções no docker-compose (U-003)
- `api` e `worker` agora têm `MINIO_ENDPOINT: http://minio:9000` (hostname da
  rede `infra-net`; `localhost` num container aponta para ele mesmo → 111).
- `command` do `api` usa `$${API_WORKERS:-1}` — o compose não interpola o
  `$API_WORKERS` vazio (antes gerava `uvicorn --workers --factory`).

### Docs
- `docs/insomnia/einstein-test-api.json`: request `POST /files/batch` (upload
  múltiplo, F-030) + variável `file_path_2` (estava pendente).

## Critérios de aceite implementados

| AC | História | Status | Prova |
|----|----------|--------|-------|
| AC-001 | U-001 — `ensure_bucket` idempotente (cria se ausente; erro não-404 propaga; indisponível loga) | PASS | `tests/infra/test_storage_bucket.py -k 'ensure_bucket and not noop'` |
| AC-002 | U-001 — InMemory no-op; lifespan do app chama `ensure_bucket` | PASS | `tests/infra/test_storage_bucket.py -k 'noop or lifespan'` |
| AC-003 | U-002 — entrypoint roda `alembic upgrade head` + `exec "$@"` (retry, exit 1) | PASS | `tests/infra/test_docker.py -k 'entrypoint'` |
| AC-004 | U-002 — Dockerfile copia alembic + define ENTRYPOINT | PASS | `tests/infra/test_docker.py -k 'dockerfile or versions'` |
| AC-005 | U-003 — compose com `MINIO_ENDPOINT` interno e fallback de workers | PASS | `tests/infra/test_infra_docker.py -k 'api or network'` |

## Veredito mecânico
`specs proof --strict F-033-infra-boot` → `PASS` (5/5 ACs).
`uv run pytest -m "not integration"` → `398 passed, 1 deselected`.
`ruff check .` → all passed.

## Deep review (F4)
6 subagentes `review-*` sobre o diff; achados corrigidos:
- **Corrida de criação de bucket** (major, security/correctness): `create_bucket`
  sob `API_WORKERS > 1` podia lançar `BucketAlreadyOwnedByYou` e derrubar o
  worker; tratado como sucesso, e indisponibilidade no create também loga/sai.
- **Corrida de migrations api+worker** (major, correctness/performance):
  `alembic/env.py` agora usa `pg_advisory_lock` para serializar `upgrade head`.
- **AC-005 sem teste** (major, tests): novos testes do compose para
  `MINIO_ENDPOINT` (api/worker) e `$${API_WORKERS:-1}`.
- **Branch indisponível sem teste** (major, tests): coberto via fake com
  `ConnectionError` no head e no create; `NoSuchBucket` e corrida 409 também
  testados.
- **Nits**: logger morto removido do `main.py`; `bucket` adicionado ao
  `_KNOWN_FIELDS` do JsonFormatter (não era logado).

## Como usar
```bash
# boot com tudo automático (migrations + bucket):
docker compose up -d --build api worker
# logs do boot:
docker compose logs api | grep -i "entrypoint\|migration"
```
- bucket `einstein` criado sozinho no startup da API;
- migrations aplicadas antes de uvicorn/celery; falha de banco → retry (padrão
  10x com 2s) e `exit 1`.

## Arquivos
- `src/einstein_test/storage/minio.py` (`ensure_bucket`, BUCKET)
- `src/einstein_test/storage/inmemory.py` (`ensure_bucket` no-op)
- `src/einstein_test/main.py` (lifespan chama `get_storage().ensure_bucket()`)
- `docker/entrypoint.sh` (novo — migrations no boot com retry)
- `Dockerfile` (copia alembic + ENTRYPOINT)
- `docker-compose.yml` (`MINIO_ENDPOINT`, `$${API_WORKERS:-1}`)
- `docs/insomnia/einstein-test-api.json` (endpoint batch do F-030)
- `tests/conftest.py` (`_storage_fake` autouse)
- `tests/infra/test_storage_bucket.py` (novo), `tests/infra/test_docker.py`