# F-001 — Infra local docker compose

## O que foi feito
Stack de infra local via Docker Compose: **PostgreSQL com pgvector** (desde
F-009) e **MinIO** (compatível S3), ambos saudáveis (healthcheck), persistentes
(volumes nomeados) e isolados em rede dedicada.

> **Nota (F-009):** a inicialização automática de bucket (`minio-init`) foi
> removida na F-009; o bucket `einstein` agora se cria manualmente (console
> web `:9001` ou boto3). Ver `docs/features/F-009-fix-minio-image.md`.

## Critérios de aceite implementados

| AC | História | Status | Prova |
|----|----------|--------|-------|
| AC-001 | U-001 — registro local do PostgreSQL | PASS | `tests/test_infra_docker.py` (`ankane/pgvector` (pgvector, desde F-009), `pg_isready`, volume `pgdata`, porta `5432:5432`, rede `infra-net`) |
| AC-002 | U-001 — registro local do MinIO | PASS | `tests/test_infra_docker.py` (`minio/minio`, healthcheck `/minio/health/live`, volume `minio-data`, portas `9000/9001`, rede `infra-net`) |
| AC-003 | U-002 — banco de teste separado | PASS | `docker/initdb/create-test-db.sh` cria `einstein_test` com owner `$POSTGRES_USER` |
| AC-004 | U-003 — bucket padrão no 1º boot | PASS (F-001) → **superado pela F-009** | `minio-init` removido na F-009; bucket agora manual |
| AC-005 | U-001 — compose válido + rede dedicada | PASS | `docker compose config` exit 0 + network `infra-net` com nome explícito |

## Veredito mecânico
`specs proof --strict F-001-infra-local` → `PASS` (5/5 ACs, 11 testes). `specs gate` → `PASS`.

## Como usar
```sh
docker compose up -d        # sobe postgres + minio
docker compose ps           # healthchecks
docker compose down         # derruba (dados ficam nos volumes pgdata/minio-data)
```

Endpoints:
- PostgreSQL → `localhost:5432` (user `einstein`, senha `einstein`, db `einstein` e `einstein_test`)
- MinIO API → `localhost:9000` · Console → `localhost:9001` (user/senha `minioadmin`)
- Bucket padrão: `einstein` (criação manual — ver F-009)

## Notas
- A-002 confirmada: imagem MinIO via tag `latest` (release estável atual).
- Bloqueio ambiental observado: o registry deste ambiente recusa `minio/mc`
  (imagem do cliente, usada pelo `minio-init`). O `minio/minio` (servidor)
  puxa normalmente. O compose mantém as imagens oficiais — o bloqueio é do
  ambiente, não do código.