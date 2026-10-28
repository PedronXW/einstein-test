# F-033 — Boot automático de infra: bucket MinIO + migrations alembic

## Resumo
Hoje, ao subir a aplicação:
- o **bucket `einstein` do MinIO** precisa ser criado manualmente (senão o upload
  de arquivos falha com 404/111);
- as **migrations alembic** só rodam no CI — o container sobe sem aplicar o
  schema (tabelas/colunas novas ausentes em runtime);
- o `docker-compose.yml` tem bugs de infra: `MINIO_ENDPOINT` aponta para
  `localhost` dentro do container (deveria ser o hostname `minio` da rede) e o
  `command` do `api` interpola `$API_WORKERS` vazio (quebra o uvicorn).

Esta feature automatiza o boot de infra: **bucket criado no startup da app** e
**migrations aplicadas no boot do container** (api e worker), além de corrigir
o compose. Inclui ainda a doc do Insomnia para o endpoint de upload múltiplo
(F-030) que havia ficado pendente.

## Histórias de usuário
- U-001 — **Como** operador, **quero** que o bucket do MinIO seja criado
  automaticamente no startup da app, **para** não precisar criar manualmente a
  cada `docker compose up` (ou após `down -v`).
- U-002 — **Como** desenvolvedor, **quero** que as migrations alembic rodem no
  boot do container, **para** a API e o worker sempre subirem com o schema em dia.
- U-003 — **Como** operador, **quero** que o compose aponte a API/worker para o
  MinIO correto (hostname `minio`) e aceite workers com fallback, **para** o
  upload de arquivos funcionar em container e o boot não quebrar.

## Critérios de aceite
> Critérios são registrados mecanicamente (AC-### → story → semântica técnica → dono T-###)
> — edite `criteria.reg` e reflita aqui por legibilidade ponto a ponto.

- AC-001 — [U-001] `MinioStorage.ensure_bucket(name)` verifica (`head_bucket`)
  e cria o bucket se ausente (`create_bucket`); idempotente; erro não-"bucket
  ausente" propaga; indisponibilidade do MinIO no boot apenas loga erro.
- AC-002 — [U-001] `InMemoryStorage.ensure_bucket` é um no-op; o lifespan do
  `create_app` chama `get_storage().ensure_bucket()`
- AC-003 — [U-002] `docker/entrypoint.sh` roda `alembic upgrade head` antes do
  comando real (`exec "$@"`), com retry configurável (`MIGRATE_MAX_RETRIES`/
  `MIGRATE_RETRY_DELAY`) e exit 1 ao esgotar tentativas.
- AC-004 — [U-002] `Dockerfile` copia `alembic.ini`, `alembic/` e o entrypoint;
  define `ENTRYPOINT` (aplica para api e worker).
- AC-005 — [U-003] `docker-compose.yml`: api/worker têm `MINIO_ENDPOINT:
  http://minio:9000`; `command` do api usa `$${API_WORKERS:-1}` (sem
  interpolação vazia do compose).

## Suposições (status: aberto|confirmada|rejeitada)
- A-001 — bucket `einstein` é o bucket da aplicação (BUCKET em storage/minio.py) — confirmada.
- A-002 — migrations são idempotentes (alembic `upgrade head` no schema atual é no-op) — confirmada.
- A-003 — testes não devem tocar MinIO real: fixture autouse `_storage_fake`
  usa `InMemoryStorage`; `ensure_bucket` é testado com fake do boto3 — confirmada.

## Perguntas em aberto
- Q-001 — Onde criar o bucket? → `MinioStorage.ensure_bucket` idempotente via
  lifespan do create_app (resolvida).
- Q-002 — Onde rodar migrations? → entrypoint do container (api e worker herdam
  do Dockerfile), com retry — resolvida.