# F-001 — Infra local docker compose

## Resumo
Subir a infraestrutura local de desenvolvimento via `docker compose`:
um banco **PostgreSQL 16** (alpine) e um **MinIO** (S3) com bucket inicial,
saudáveis (healthcheck), com dados persistentes (volumes) e rede dedicada.

## Histórias de usuário
- U-001 — **Como** dev local, **quero** subir PostgreSQL e MinIO com um único
  `docker compose up`, **para** ter banco e S3 equivalentes ao ambiente real sem config manual.
- U-002 — **Como** dev local, **quero** um banco de teste separado criado junto
  (mesmo user/password do principal), **para** rodar testes sem poluir dados de dev.
- U-003 — **Como** dev local, **quero** que um bucket padrão exista no MinIO já
  no primeiro boot, **para** a aplicação enxergar storage pronto sem passo manual.

## Critérios de aceite
> Critérios são registrados mecanicamente (AC-### → story → semântica técnica → dono T-###)
> — edite `criteria.reg` e reflita aqui por legibilidade ponto a ponto.

- AC-001 — [U-001] Serviço `postgres` declarado com imagem `postgres:16-alpine`,
  healthcheck (`pg_isready`), volume persistente nomeado e porta `5432:5432` na rede dedicada.
- AC-002 — [U-001] Serviço `minio` declarado com imagem MinIO (release estável atual),
  healthcheck (curl no health endpoint), volume persistente nomeado e portas
  `9000:9000` (API) e `9001:9001` (console) na rede dedicada.
- AC-003 — [U-002] Banco de teste `einstein_test` criado automaticamente no primeiro
  boot do postgres (init de `<POSTGRES_DB>_test`), herdando o mesmo user do principal.
- AC-004 — [U-003] Bucket padrão `einstein` criado no MinIO no primeiro boot
  (serviço `minio-init` com `minio/mc` + alias + `mc mb`).
- AC-005 — [U-001] `docker compose config` valida e ambos os serviços compartilham
  uma rede dedicada nomeada (network própria, isolada da `default`).

## Suposições (status: aberto|confirmada|rejeitada)
- A-001 — Credenciais do banco definidas como variáveis no compose
  (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`) com valores de dev; sem `.env` externo. — confirmada
- A-002 — Imagem MinIO na tag `latest` (release estável atual, escolha do usuário). — confirmada
- A-003 — Portas fixas no host: `5432` (postgres), `9000` (minio API), `9001` (minio console). — confirmada
- A-004 — Volumes nomeados `pgdata` e `minio-data` garantem persistência. — confirmada
- A-005 — Banco de teste nomeado `<POSTGRES_DB>_test` (ou seja `einstein_test`). — confirmada
- A-006 — Healthchecks com `pg_isready` (postgres) e `curl` ao `/minio/health/live` (minio). — confirmada

## Perguntas em aberto
- (nenhuma)