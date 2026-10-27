# F-009 — Infra: remover minio-init + postgres vetorizado (pgvector)

## Resumo
Duas mudanças de infra no docker compose:
1. **Remover o serviço `minio-init`** (imagem `minio/mc`) — a inicialização
   automática de bucket causava erro de pull (`pull access denied` p/ `minio/mc`
   no registry deste ambiente). O MinIO (`minio/minio`) é mantido; bucket
   `einstein` passa a ser manual.
2. **Postgres vetorizado**: trocar `postgres:16-alpine` por
   **`ankane/pgvector:latest`** (PostgreSQL 16 + extensão `vector`), para
   embeddings/vector search futuros. O init do banco de teste (F-001) continua.

## Histórias de usuário
- U-001 — **Como** dev, **quero** que `docker compose up` não falhe por causa do
  `minio-init` (que puxa `minio/mc` bloqueada no registry), **para** subir a
  infra local sem erro de pull.
- U-002 — **Como** dev, **quero** continuar usando MinIO (`minio/minio`) como
  storage S3 local com mesmas portas/credenciais, **para** nada além da
  inicialização automática mudar.
- U-003 — **Como** dev, **quero** que o postgres do compose seja a versão com
  pgvector (`ankane/pgvector:latest`), **para** usar colunas `vector`/
  embeddings futuros sem instalação extra.

## Critérios de aceite
- AC-001 — [U-001/U-002] `docker-compose.yml` mantém `minio` (`minio/minio:latest`,
  healthcheck `/minio/health/live`, portas `9000:9000`/`9001:9001`, volume
  `minio-data`, rede `infra-net`) e **remove** `minio-init` (sem `minio/mc`,
  sem `mc mb`).
- AC-002 — [U-001] `docker compose config` válido; as únicas imagens do compose
  são `ankane/pgvector`, `minio/minio` (sem `minio/mc`/`minio-init`).
- AC-003 — [U-002] Storage boto3 (`MinioStorage`) mantiene default
  `http://localhost:9000` (MinIO) — nada de storage muda.
- AC-004 — [U-003] Serviço `postgres` usa `ankane/pgvector:latest`; extensão
  `vector` disponível; init de banco de teste da F-001 preservado (volume
  `docker-entrypoint-initdb.d` + `create-test-db.sh`).

## Suposições
- A-001 — Bucket `einstein` passa a ser criado manualmente quando necessário;
  sin init automático. — confirmada
- A-002 — A demais infra (rede, volumes, postgres init) permanece. — confirmada
- A-003 — `ankane/pgvector:latest` puxa OK no registry (já em cache). **Nota: é
  PostgreSQL 15.4** — requere recriar o volume `pgdata` (`docker compose down -v`)
  se ele foi inicializado com postgres 16. — confirmada

## Perguntas em aberto
- (nenhuma)