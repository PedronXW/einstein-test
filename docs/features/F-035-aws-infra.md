# F-035 — Infra AWS com Terraform (prod) + deploy via GitHub Actions

## O que foi feito
Infra **100% Terraform** para a aplicação (ambiente único `prod`) espelhando o
`docker-compose.yml` local, **já conectada** — api e worker sobem com banco,
redis, S3 e secrets prontos. Deploy **manual** via GitHub Actions (`Run
workflow`): job `infra` (terraform) → job `app` (build ECR + rollout ECS).

### Infra provisionada (U-001)
| Local (compose) | AWS (Terraform) |
|-----------------|------------------|
| Postgres + pgvector | RDS PostgreSQL 15.19 (`CREATE EXTENSION vector` na migration inicial) |
| MinIO + bucket `einstein` | S3 `einstein-prod-files` (cripto + versioning) |
| Redis (broker Celery/rate-limit) | ElastiCache Redis 7 single-node |
| `api` (uvicorn) | ECS Fargate service `einstein-prod-api` atrás de ALB |
| `worker` (celery) | ECS Fargate service `einstein-prod-worker` |
| Secrets por env | AWS Secrets Manager (`einstein-test/prod/...`) |
| `entrypoint.sh` (migrations+bucket) | Mantido — roda no boot da 1ª task |
| — | VPC 2 AZs, NAT, SGs, ECR, IAM/OIDC, CloudWatch Logs, autoscaling |

### Deploy manual via GitHub Actions (U-002)
- `.github/workflows/deploy.yml` disparado por **`workflow_dispatch`** (botão
  **Run workflow** na aba Actions; sem push em main). Input `environment`
  (`prod`).
- Job `infra`: assume role `einstein-prod-github-infra` (OIDC, sem chaves) →
  `terraform plan+apply -var-file=envs/prod.tfvars`.
- Job `app` (needs infra): assume `einstein-prod-github-app` → build + push
  ECR (`prod-<sha>` e `latest`) → `deploy/rollout.sh prod <imagem>` registra
  nova revisão dos task defs e faz `update-service` (rolling) + `wait
  services-stable`.
- Migrations e bucket continuam no boot da task (`docker/entrypoint.sh`).

### Ajustes na aplicação (U-003)
- `src/einstein_test/storage/minio.py`
  - bucket configurável via `S3_BUCKET` (default `einstein`); no AWS o TF passa
    `einstein-prod-files` e o `ensure_bucket` vira um no-op idempotente.
  - credenciais: prioriza `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` →
    `MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD` → provider chain do boto3 (task role
    do ECS). Sem mais `minioadmin` hardcoded. `S3_ENDPOINT_URL` explícito aponta
    para o S3 regional; local (compose) continua via `MINIO_ENDPOINT`.
- Nada mais muda: migrations/bucket já rodam no `entrypoint.sh` (alembic com
  advisory lock + retry), inclusive na 1ª subida no Fargate.

## Critérios de aceite implementados

| AC | História | Status | Prova |
|----|----------|--------|-------|
| AC-001 | U-001 — Terraform cobre VPC, RDS+pgvector, Redis, S3, Secrets, ECR, IAM/OIDC, ECS+ALB, logs, autoscaling | PASS | `terraform validate` (raiz + bootstrap) e `apply` concluído (55 recursos) |
| AC-002 | U-002 — Deploy manual via GitHub Actions (workflow_dispatch; infra + ECR + rollout) | PASS | `.github/workflows/deploy.yml` + `deploy/rollout.sh` |
| AC-003 | U-003 — App conecta em S3 via task role (sem keys) e bucket configurável | PASS | `tests/infra/test_storage_bucket.py`, `tests/services/test_file_service.py` |
| AC-004 | U-004 — Migrations/bucket no boot mantidos no Fargate | PASS | `docker/entrypoint.sh` (inalterado); migrações aplicadas no RDS no 1º boot |

## Veredito mecânico
- `terraform validate` → `Success` em `terraform/` e `terraform/bootstrap/`.
- `terraform plan -var-file=envs/prod.tfvars` → `Plan: 55 to add, 0 to change,
  0 to destroy` (antes do 1º apply).
- `terraform apply` → `Apply complete! Resources: 2 added` (retomada) — stack
  completa provisionada.
- `uv run pytest -m "not integration"` → `420 passed, 1 deselected`.
- `ruff check .` → all passed.
- Rollout local `deploy/rollout.sh` → `deploy concluído (env=prod)`;
  `aws ecs describe-services` → api e worker **1/1 running**; `GET /health` no
  ALB → **200**; migrações no RDS confirmadas no CloudWatch (`Running upgrade
  ... -> c19610cbe5e6`).

## Como usar

### 1) Bootstrap (uma única vez, com credenciais de admin da AWS)
```bash
aws configure  # perfil com permissão para criar IAM/S3/DynamoDB
cd terraform/bootstrap
terraform init && terraform apply -auto-approve
```
Cria: bucket `einstein-test-tfstate-prod`, tabela de lock
`einstein-test-tfstate-locks-prod`, OIDC do GitHub e as roles
`einstein-prod-github-infra`/`einstein-prod-github-app`.

### 2) Secrets do GitHub (Settings → Secrets and variables → Actions)
- `AWS_ACCOUNT_ID` — id da conta AWS (as roles do passo 1 atuam nele).
- `OPENAI_API_KEY` — chave da API OpenAI-compatível (vai para o Secrets Manager).

### 3) Deploy manual
1. Aba **Actions** → workflow **Deploy** → **Run workflow** (branch `main`,
   environment `prod`).
2. O job `infra` aplica o terraform; o job `app` faz build → push ECR →
   rollout (api + worker) e aguarda estabilização.

### 4) Endpoints e conexões
- **API**: `http://einstein-prod-alb-1485984983.us-east-1.elb.amazonaws.com`
  (`terraform output alb_dns_name`) — porta 80, `/health` → 200.
- **Banco**: RDS privado `einstein-prod.c948secswu4n.us-east-1.rds.amazonaws.com`
  (`terraform output rds_address`), SG só libera dos tasks.
- **Redis**: ElastiCache privado `einstein-prod.oaxkvn.ng.0001.use1.cache.amazonaws.com`
  (`terraform output redis_endpoint`).
- **S3**: bucket `einstein-prod-files`; task role assume acesso (sem keys).
- **Secrets**: `terraform output secrets_app_arn` (JWT, OPENAI_API_KEY, URLs).

## Notas e custos
- NAT gateway + RDS/ElastiCache pequenos (~US$ 40–80/mês); autoscaling por CPU
  limita a conta. `rds_multi_az=false` por padrão.
- Sem domínio/TLS ainda (só HTTP). Para HTTPS: `aws_acm_certificate` + listener
  443 no `load_balancer.tf` (deixado de fora para não travar o 1º apply).
- As roles do GitHub são de **bootstrap** (aplicadas manualmente) para o CI
  poder assumi-las desde o 1º run — evita o chicken-egg de o CI criar as
  próprias roles.
- A role `github-infra` anexa políticas gerenciadas amplas (provisão completa
  da stack). Reduza para least-privilege se necessário.
- **Peculiaridades da AWS resolvidas no apply:**
  - as policies gerenciadas `AmazonElasticLoadBalancing*` não existem mais —
    o ELB é coberto por policy própria (`github_infra_elb`);
  - a execution role do ECS também precisa de `secretsmanager:GetSecretValue`
    (o agente do ECS busca os secrets no start da task, não a task role);
  - `aws_ecs_service` usa `lifecycle { ignore_changes = [task_definition] }` —
    senão o `terraform apply` reverte o serviço para a revisão inicial do task
    def, desfazendo o rollout do CI/CD;
  - versão do RDS validada como `15.19` (o `15.8` não existe mais no catálogo).

## Arquivos
- `terraform/bootstrap/{providers,state,roles,variables}.tf` (novos)
- `terraform/{backend,versions,providers,variables,network,database,cache,storage,secrets,container_registry,iam,ecs,load_balancer,observability,outputs}.tf` (novos)
- `terraform/envs/prod.tfvars` (novo)
- `.github/workflows/deploy.yml` (novo)
- `deploy/rollout.sh` (novo)
- `src/einstein_test/storage/minio.py` (ajuste S3/IAM + `S3_BUCKET`)
- `docs/features/F-035-aws-infra.md` (este)
