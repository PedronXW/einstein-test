# einstein-test

**API de conversa fundamentada em arquivos (RAG)** — envie documentos para um chat, a aplicação os vetoriza e responde perguntas com base apenas no conteúdo deles.

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.162-009688?logo=fastapi&logoColor=white)
![PostgreSQL+pgvector](https://img.shields.io/badge/PostgreSQL-15%2B-4169E1?logo=postgresql&logoColor=white)
![Tests](https://img.shields.io/badge/tests-475%20passed-brightgreen)
![Lint](https://img.shields.io/badge/ruff-lint%20ok-brightgreen)

---

## Índice

- [Sobre](#sobre)
- [Funcionalidades](#funcionalidades)
- [Arquitetura](#arquitetura)
- [Base de conhecimento (RAG)](#base-de-conhecimento-rag)
- [Como executar](#como-executar)
- [Endpoints da API](#endpoints-da-api)
- [Como testar](#como-testar)
- [Avaliação do RAG (harness)](#avaliação-do-rag-harness)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Principais decisões técnicas](#principais-decisões-técnicas)
- [Como a IA foi usada no desenvolvimento](#como-a-ia-foi-usada-no-desenvolvimento)
- [Documentação das features](#documentação-das-features)

---

## Sobre

O `einstein-test` é um assistente de **perguntas e respostas sobre documentos**:

1. Você cria um usuário e um **chat**;
2. Envia **arquivos** (PDF, texto etc.) para o chat — eles são quebrados em *chunks* e **vetorizados** em background;
3. Você pergunta algo no chat;
4. A API busca os chunks mais relevantes do **seu** chat, monta um contexto e o **LLM** responde com base **apenas** nesse conteúdo (tokens fluindo via SSE).

Tudo é multi-tenant por chat e por usuário: nenhum arquivo de um chat é usado para responder perguntas de outro.

---

## Funcionalidades

- **Upload e vetorização assíncrona** de arquivos (Celery + Redis, com retry e backoff);
- **Busca vetorial por similaridade** (pgvector + índice HNSW) filtrada por chat;
- **Resposta com streaming** (Server-Sent Events) e *notices* quando não há arquivos prontos;
- **Autenticação JWT** com bcrypt e **rate limiting** por usuário/IP;
- **Paginação** padronizada (`{items, page, page_size, total, total_pages}`) nos endpoints de listagem;
- **Alembic** para migrações com *advisory lock* (seguro para rodar em boot concorrente de api/worker);
- **OpenAPI/Swagger** automático em `/docs`.

---

## Arquitetura

```mermaid
flowchart LR
    C[Cliente] -->|HTTPS| A[FastAPI api]
    A -->|enfileira vetorização| W[Celery worker]
    A <-->|reads/writes| P[(PostgreSQL + pgvector)]
    W <-->|chunks + embeddings| P
    W <-->|arquivos| S[(MinIO / S3)]
    A <-->|broker/result| R[(Redis)]
    A -->|embeddings| E[Embedder OpenAI-compatível]
    A -->|prompt + contexto| L[LLM OpenAI-compatível]
```

**Fluxo do RAG**

```mermaid
sequenceDiagram
    participant U as Usuário
    participant A as API
    participant W as Worker
    participant P as pgvector
    participant L as LLM

    U->>A: upload arquivo
    A->>W: enfileira vetorização
    W->>W: split em chunks + embeddings (1536 dims)
    W->>P: INSERT file_chunks (embedding)
    U->>A: pergunta (mensagem)
    A->>P: busca chunks similares do chat (KNN)
    P-->>A: top chunks
    A->>L: prompt (contexto + histórico + pergunta)
    L-->>U: resposta via SSE
```

A aplicação segue uma arquitetura **em camadas** com regras mecânicas de *layering*:

```
api (controllers) → services (regras de negócio) → repositories → models (SQLAlchemy)
```

Os controllers **não** chamam repositórios diretamente nem definem regras de negócio — isso é validado por testes (`tests/api/test_layering_rule.py`).

---

## Base de conhecimento (RAG)

A "base de conhecimento" é o conjunto de arquivos enviados aos chats, processados assim:

| Etapa | O que acontece | Onde vive |
|---|---|---|
| **Upload** | Arquivo validado (tipo, tamanho, duplicidade) e salvo no storage | MinIO (local) / S3 (prod) |
| **Chunking** | Texto extraído e dividido em pedaços | — |
| **Embedding** | Cada chunk vira um vetor de **1536 dimensões** (`cohere/embed-v4.0` via endpoint OpenAI-compatível) | tabela `file_chunks` |
| **Indexação** | Índice **HNSW** sobre `embedding` com `vector_cosine_ops` (busca por aproximação) | pgvector |
| **Retrieval** | Busca os chunks mais similares **do chat** (`ORDER BY embedding <=> query`) com limite de candidatos | pgvector + re-rank em Python |
| **Re-rank** | Máx. **2 chunks por arquivo**, teto global de **12**, ordenados por similaridade | `vector/similarity.py` |
| **Geração** | Prompt = contexto + histórico + pergunta → LLM | LangGraph (retrieve → generate) |

Isolamento: a busca só considera `file_id` de arquivos do chat do usuário autenticado; embeddings de outros chats nunca entram no contexto.

> O índice HNSW é **global** (uma estrutura sobre `file_chunks.embedding`) e **usado pelo planner quando vantajoso** — chats pequenos/médios usam o índice FK + sort (rápido e exato), e chats grandes passam a usar o scan HNSW. Mais detalhes em `docs/features/F-037-hnsw-search.md`.

---

## Como executar

### Pré-requisitos

- **Docker + Docker Compose** (recomendado) **ou** Python **3.12** + [uv](https://docs.astral.sh/uv/);
- Uma **chave da API OpenAI-compatível** (`OPENAI_API_KEY`).

### 1) Rodar com Docker Compose (recomendado)

```bash
cp .env.example .env            # preencha OPENAI_API_KEY e JWT_SECRET
docker compose up --build
```

Ao subir, o compose inicializa **PostgreSQL + pgvector**, **MinIO**, **Redis**, a **API** e o **worker** Celery. As migrações rodam no boot (entrypoint com *advisory lock*).

- API: <http://localhost:8000>
- Swagger UI: <http://localhost:8000/docs>
- Healthcheck: <http://localhost:8000/health>
- Console do MinIO: <http://localhost:9001> (`minioadmin` / `minioadmin`)

### 2) Rodar sem Docker (com uv)

Suba apenas a infra e rode a aplicação localmente:

```bash
# 1) infra (postgres+pgvector, minio, redis)
docker compose up -d postgres minio redis

# 2) dependências
uv sync --dev

# 3) variáveis de ambiente (base local)
export OPENAI_API_KEY=...                # obrigatório
export JWT_SECRET=$(openssl rand -hex 32)
export DATABASE_URL=postgresql://einstein:einstein@localhost:5432/einstein
export CELERY_BROKER_URL=redis://localhost:6379/0
export CELERY_RESULT_BACKEND=redis://localhost:6379/0
export MINIO_ENDPOINT=http://localhost:9000
export MINIO_ROOT_USER=minioadmin        # credenciais do MinIO do compose
export MINIO_ROOT_PASSWORD=minioadmin

# 4) migrações
uv run alembic upgrade head
uv run alembic check                   # garante models == migrations

# 5) API + worker
uv run uvicorn einstein_test.main:create_app --factory --reload --port 8000
uv run celery -A einstein_test.tasks worker --loglevel=info
```

---

## Endpoints da API

Autenticação via header `Authorization: Bearer <access_token>` (obtido no login).

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/health` | Healthcheck (SELECT 1) |
| `POST` | `/users` | Criar usuário (201) |
| `POST` | `/auth/login` | Login → `{access_token, token_type}` |
| `GET` | `/users/me` | Perfil do usuário |
| `PATCH` | `/users/me` | Atualizar perfil (ex.: modelo de LLM) |
| `POST` | `/chats` | Criar chat |
| `GET` | `/chats` | Listar chats (paginado) |
| `GET` | `/chats/{chat_id}` | Detalhe do chat |
| `DELETE` | `/chats/{chat_id}` | Deletar chat (soft delete) |
| `POST` | `/chats/{chat_id}/messages` | Enviar mensagem → **SSE** com a resposta |
| `GET` | `/chats/{chat_id}/messages` | Histórico (paginado, ordem cronológica) |
| `GET` | `/messages/{message_id}` | Detalhe da mensagem |
| `DELETE` | `/messages/{message_id}` | Deletar mensagem |
| `POST` | `/chats/{chat_id}/files` | Upload de arquivo (202, vetoriza em background) |
| `POST` | `/chats/{chat_id}/files/batch` | Upload de múltiplos arquivos (207) |
| `GET` | `/chats/{chat_id}/files` | Listar arquivos (paginado) |
| `GET` | `/files/{file_id}` | Detalhe do arquivo |
| `DELETE` | `/files/{file_id}` | Deletar arquivo |

### Exemplo de fluxo completo

```bash
BASE=http://localhost:8000

# 1) usuário
curl -s -X POST $BASE/users \
  -H 'Content-Type: application/json' \
  -d '{"email":"voce@b.com","password":"senha123"}'

# 2) login
TOKEN=$(curl -s -X POST $BASE/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"voce@b.com","password":"senha123"}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

AUTH="Authorization: Bearer $TOKEN"

# 3) chat
CHAT=$(curl -s -X POST $BASE/chats -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"name":"meu chat"}')
CHAT_ID=$(echo "$CHAT" | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')

# 4) upload de arquivo (vetorização roda em background)
curl -s -X POST $BASE/chats/$CHAT_ID/files -H "$AUTH" \
  -F 'file=@./exemplo.txt;type=text/plain'

# 5) perguntar (resposta streamada via SSE)
curl -N -X POST $BASE/chats/$CHAT_ID/messages -H "$AUTH" \
  -H 'Content-Type: application/json' \
  -d '{"content":"Sobre o que fala o arquivo?"}'
```

> Paginação nos endpoints de listagem: `?page=1&page_size=20` (máx. 100; valores fora → 422).

---

## Como testar

```bash
# Lint
uv run ruff check .

# Migrations (aplica + confere drift)
uv run alembic upgrade head
uv run alembic check

# Testes unitários + de API/serviços (sem integração)
uv run pytest -m "not integration"

# Com cobertura
uv run pytest -m "not integration" --cov=einstein_test --cov-report=term
```

### Testes de integração (RAG end-to-end com provedor real)

Exigem `OPENAI_API_KEY`, infra de pé e `RUN_INTEGRATION=1`:

```bash
export RUN_INTEGRATION=1
uv run pytest -m integration
```

---

## Avaliação do RAG (harness)

O projeto inclui um **harness de avaliação** (`src/einstein_test/eval/`, feature
F-038) para medir, por evidência, a qualidade do RAG:

| Dimensão | O que mede |
|---|---|
| **Retrieval** | `recall@5`, `recall@12`, `MRR@5`, `hit@1` — o contexto certo foi recuperado? |
| **Assertividade** | `correctness` — resposta correta vs. gold (1–5) |
| **Fidelidade** | `faithfulness` — resposta ancorada no contexto, sem alucinação (1–5) |
| **Cobertura** | `coverage` — a resposta cobre a pergunta (1–5) |
| **Robustez** | pergunta fora do corpus não deve fabricar resposta |
| **Perf/custo** | TTFT, latência total, tokens por pergunta |
| **Similaridade** | cosseno entre resposta e gold (paráfrases penalizam um pouco) |

### Dataset gold
`eval/dataset/dev.jsonl` — perguntas com `expected_files` (quais documentos
contêm a resposta) e `gold_answer` (resposta ideal). O corpus fica em
`eval/corpus/` (documentos sintéticos com fatos exatos + documentos naturais).

### Como rodar

**Smoke determinístico (fakes, sem chave — CI):**
```bash
uv run python -m einstein_test.eval --backend fake --limit 2 --format md
```

**Avaliação real** (requer `OPENAI_API_KEY`, infra de pé e banco local):
```bash
docker compose up -d postgres minio redis
uv run alembic upgrade head
set -a; source .env; set +a
export DATABASE_URL=postgresql://einstein:einstein@localhost:5432/einstein

uv run python -m einstein_test.eval --backend real --judge llm \
  --format html --out eval/reports/latest.html
```

Variantes úteis: `--limit N` (controla custo), `--judge fake` (sem custo de
juiz), `--format md|html|json`. O `--backend real` vetoriza o corpus de
verdade, roda o RAG real e **limpa** as linhas criadas no banco ao final; só
roda em banco local sem `EVAL_ALLOW_NON_LOCAL=1`.

### O que usa o sistema real vs. parametrizado
- **Real**: embeddings, busca pgvector (KNN/HNSW), geração via LLM, storage.
- **Parametrizado (ground truth)**: as perguntas/`expected_files`/`gold_answer`
  — o sistema nunca vê o gold durante a execução.

### Erros encontrados e corrigidos durante o desenvolvimento
- **`RuntimeError: Event loop is closed`** — o run por pergunta usando
  `asyncio.run()` fechava o event loop enquanto o cliente async do LLM
  (langchain/httpx) ainda o referenciava. Corrigido reutilizando **um único
  event loop** em todas as perguntas.
- **`recall@5 = 0.0` no backend real** — a ingestão do corpus rodava dentro de
  `with Session(...)` sem commit; no exit o rollback descartava as linhas e os
  chunks nunca eram persistidos. Corrigido com `s.commit()` ao fim da ingestão.

### Limitações conhecidas
- O harness chama o RAG **in-process** (não passa pela camada HTTP); o gate de
  `no_ready_files` da API não é exercitado — uma pergunta fora do corpus pode
  ser respondida (alucinação) em vez de receber o *notice* da aplicação.
- O `LLMJudge` ainda é **leniente** com resposta não-ancorada (scorou `5.0` em
  fidelidade para um caso sem contexto). Ajuste de rubric pendente.
- Cada pergunta usa um chat "limpo" (só os arquivos esperados, sem
  *distractors*) — recall otimista vs. chats ruidosos.

---

## Variáveis de ambiente

Copie `.env.example` para `.env` e preencha:

| Variável | Default | Descrição |
|---|---|---|
| `OPENAI_API_KEY` | — | **Obrigatória.** Chave do endpoint OpenAI-compatível |
| `OPENAI_BASE_URL` | `https://spillway.ensinoeinstein.com/openai/v1` | Base URL do embedder/LLM |
| `OPENAI_MODEL` | `cohere/embed-v4.0` | Modelo de embedding (1536 dims) |
| `OPENAI_EMBEDDING_DIM` | `1536` | Dimensão do embedding |
| `OPENAI_CHAT_MODEL` | `azure/gpt-5-mini` | Modelo de chat do RAG |
| `JWT_SECRET` | — | **Obrigatória.** Segredo JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Validade do token |
| `DATABASE_POOL_SIZE` | `10` | Pool de conexões do Postgres |
| `DATABASE_MAX_OVERFLOW` | `20` | Conexões extras do pool |
| `DATABASE_POOL_TIMEOUT` | `30` | Timeout do pool (s) |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Broker do Celery |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/0` | Result backend do Celery |
| `MINIO_ENDPOINT` | `http://localhost:9000` | Endpoint do object storage local |
| `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` | `minioadmin` / `minioadmin` | Credenciais do MinIO local (no AWS, use `S3_ENDPOINT_URL` + task role do ECS) |
| `VECTORIZE_MAX_RETRIES` | `3` | Retries da vetorização |
| `VECTORIZE_RETRY_BACKOFF` | `2` | Backoff exponencial (s) |
| `LLM_MAX_RETRIES` | `2` | Retries do LLM antes do 1º token |
| `LLM_RETRY_BACKOFF` | `1` | Backoff do LLM (s) |
| `ALLOWED_MODELS` | `azure/gpt-5-mini,azure/gpt-6-luna` | Modelos de LLM permitidos por usuário |
| `RATE_LIMIT_*` | vários | Limites por minuto (login, chats, messages, files, users, global) |

---

## Estrutura do projeto

```
.
├── src/einstein_test/
│   ├── api/          # controllers FastAPI (auth, chats, messages, files)
│   ├── models/       # SQLAlchemy models (user, chat, message, file, file_chunk)
│   ├── repositories/ # acesso a dados (chat, message, file, user, sqlalchemy)
│   ├── services/     # regras de negócio (auth, chat, file, message, rag, pagination)
│   ├── schemas/      # Pydantic (requests/responses, Page[T])
│   ├── storage/      # abstraction de object storage (MinIO/S3, in-memory)
│   ├── tasks/        # Celery (vetorização em background)
│   ├── vector/       # pgvector: repositório vetorial + similaridade (KNN/HNSW)
│   ├── middleware/   # rate limiting, logging
│   └── db/           # Base declarativa, engine, session factory
├── alembic/          # migrations (pgvector, HNSW, backfills)
├── tests/            # unitários, API, services, vector, migrations, integração
├── terraform/        # infra AWS (VPC, RDS, ElastiCache, S3, ECR, ECS, ALB, OIDC)
├── deploy/           # rollout ECS (script)
├── docker/           # entrypoint, initdb
└── docs/features/    # documentação das features (F-001..F-037)
```

---

## Principais decisões técnicas

- **Postgres + pgvector como única base vetorial** — o RAG roda no mesmo banco relacional (sem infra vetorial extra), com tipo `vector(1536)` e índice **HNSW**.
- **Busca por similaridade com candidate-pool + re-rank** — query KNN (`ORDER BY embedding <=> query LIMIT`) que habilita o índice HNSW em escala, seguida de re-rank em Python para manter diversidade (máx. 2 chunks/arquivo, teto 12). Detalhes em `F-037-hnsw-search.md`.
- **Arquitetura em camadas com regras mecânicas** — controllers não falam com repositórios nem definem regra de negócio; isso é garantido por testes de layering.
- **Vetorização assíncrona** — Celery + Redis com retry/backoff; o upload responde 202 e o arquivo fica pronto em background.
- **Migrations seguras em boot concorrente** — Alembic com *advisory lock* (api e worker migram sem corrida). O lock é adquirido em `AUTOCOMMIT` para não disparar o autobegin do SQLAlchemy (bug de rollback corrigido na prática).
- **Autenticação JWT + bcrypt + rate limiting** por usuário/IP.
- **Paginação padronizada** — envelope `Page[T]` em todos os list endpoints.
- **Infra AWS 100% Terraform** — ECS Fargate (api + worker), RDS PostgreSQL 15.19, ElastiCache Redis 7, S3, ALB, VPC privada; deploy manual via GitHub Actions com **OIDC**.
- **Provedores OpenAI-compatíveis + allowlist de modelos** por usuário.

---

## Como a IA foi usada no desenvolvimento

O desenvolvimento foi conduzido por um **agente de IA (opencode)** seguindo um fluxo **spec-anchored** (especificação → prova mecânica → código → revisão → commit). Na prática:

- **Spec-driven com TDD mecânico** — cada feature abriu uma spec (`spec.md`, critérios `AC-###`, suposições); os testes foram escritos **antes** do código e cada critério foi registrado como **prova executável** (`specs prove`), com veredito por **exit code**, não por opinião.
- **Perguntas de clarificação** — decisões de design (formato da paginação, limites, estratégia HNSW) foram resolvidas em diálogo com o usuário antes de implementar.
- **Deep review com 6 subagentes** — a cada feature, revisores especializados (correção, segurança, compatibilidade, performance, qualidade, testes) analisaram o diff; os achados foram corrigidos de forma transparente antes do fechamento.
- **Diagnóstico baseado em evidência** — problemas reais foram caçados com ferramentas: `EXPLAIN ANALYZE` para provar o uso do índice HNSW; captura dos *claims* OIDC para descobrir a mudança de formato do `sub` do GitHub; isolamento do rollback do Alembic via autobegin.
- **Documentação por feature** — cada feature tem um doc em `docs/features/` com critérios, provas mecânicas e decisões.

O fluxo completo do pipeline: **especificar → testar → implementar → documentar → revisar → aprovar → commitar**, sempre com gates mecânicos e aprovação explícita do usuário antes de qualquer commit.

---

## Documentação das features

Cada feature (F-001..F-038) tem documentação própria em [`docs/features/`](docs/features/), incluindo:

- `F-011` — busca por similaridade (RAG) · `F-015` — Celery · `F-016` — rate limiting
- `F-017` — índice HNSW · `F-026` — CI · `F-033` — infra local · `F-035` — infra AWS
- `F-036` — paginação nos list endpoints · `F-037` — busca HNSW (candidate-pool + re-rank)
- `F-038` — harness de avaliação do RAG (assertividade, retrieval, robustez, perf)

---

## Ambiente de produção (AWS)

A aplicação também roda em **produção** na AWS (infra gerenciada por Terraform em `terraform/`):

- **API:** <http://einstein-prod-alb-1485984983.us-east-1.elb.amazonaws.com>
- **Deploy manual:** GitHub Actions → workflow **Deploy** → *Run workflow* (branch `main`, environment `prod`)
- Stack: ECS Fargate (api + worker), RDS PostgreSQL 15.19, ElastiCache Redis 7, S3, ALB, Secrets Manager, CloudWatch.
