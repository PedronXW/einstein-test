# F-022 — Seleção de modelo de análise por usuário

## O que foi feito
Cada usuário pode escolher qual modelo de LLM usar nas **análises/perguntas do
RAG**. A escolha fica em uma coluna **`User.model`** (nullable — `null` = usa o
default do ambiente). O usuário consulta e atualiza via **`GET /users/me`** e
**`PATCH /users/me {"model": ...}`**. Modelos permitidos são definidos **somente
via env** (`ALLOWED_MODELS`, default `azure/gpt-5-mini,azure/gpt-6-luna`). O
RAG agora cria um **`ChatOpenAIAdapter` por usuário** com o modelo escolhido
(substitui o singleton global do LLM; o embedder continua compartilhado).

## Critérios de aceite implementados

| AC | História | Status | Prova |
|----|----------|--------|-------|
| AC-001 | U-001 — `User.model` (nullable, default NULL) + migration; `UserRead` expõe `model` | PASS | `tests/api/test_user_model.py -k 'ac001 or ac004'` |
| AC-002 | U-002 — GET/PATCH /users/me; valida contra `ALLOWED_MODELS` (inválido→422); null restaura default | PASS | `tests/api/test_user_model.py -k ac002` |
| AC-003 | U-003 — `allowed_models()` lê `ALLOWED_MODELS` env (default 2 modelos) | PASS | `tests/api/test_user_model.py -k ac003` |
| AC-004 | U-004 — `get_rag_service(retriever, *, model)` cria adapter por usuário; singleton LLM removido (embedder compartilhado) | PASS | `tests/api/test_user_model.py -k ac004` |
| AC-005 | U-002 — PATCH inválido→422; válido→200 e GET reflete; sem model usa default; RAG chamado com model do usuário | PASS | `tests/api/test_user_model.py -k ac005` |

## Veredito mecânico
`specs proof --strict F-022-user-model` → `PASS` (5/5 ACs). `uv run pytest` →
`286 passed`.

## Mudanças na API
- **Novo**: `GET /users/me` (autenticado) → `UserRead` com `model`.
- **Novo**: `PATCH /users/me {"model": "azure/gpt-6-luna"}` → `UserRead`.
  Modelo fora de `ALLOWED_MODELS` → `422`. `{"model": null}` restaura default.
- `FileRead`/RAG: `POST /messages` usa o `model` do usuário autenticado.

## Configuração
- `ALLOWED_MODELS` (env) — lista separada por vírgula, default
  `azure/gpt-5-mini,azure/gpt-6-luna`. Documentada em `.env.example`.

## Arquivos
- `src/einstein_test/models/user.py` (`+model`), `schemas/user.py`
  (`UserRead.model`)
- `src/einstein_test/api/auth_router.py` (`GET/PATCH /users/me`,
  `UserModelUpdate`)
- `src/einstein_test/services/rag.py` (`allowed_models()`,
  `get_rag_service(..., model=)` por usuário; singleton do LLM removido)
- `src/einstein_test/api/messages.py` (passa `current_user.model` ao RAG)
- `alembic/versions/c19610cbe5e6_user_model_modelo_de_análise_selecionado.py`
- `.env.example`, `tests/api/test_user_model.py` (novo)

## Correções do deep review
- **Factory defensivo**: `get_rag_service` passa `model=` ao factory apenas
  quando não é `None` — compatível com factories antigas sem `model`.
- **Revalidation em call-time**: `POST /messages` revalida `current_user.model`
  contra `allowed_models()`; se o modelo saiu da allowlist (operador alterou o
  env), usa o default do ambiente (fail-closed no provider-call).
- **`ALLOWED_MODELS` vazia ≠ bloquear**: env ausente **ou vazia** usa o default
  (evita armadilha de `export ALLOWED_MODELS=''` derrubando a feature).
- **`UserModelUpdate.model` com `max_length=127`** (alinha à coluna; evita 500
  por valor gigante) e **`strip()`** no payload.
- `allowed_models()` chama `load_dotenv()` (consistente com o adapter).
- Testes novos: call-time fora da allowlist → default; payload com espaços
  normalizado.

## Notas
- O `ChatOpenAIAdapter` agora é criado por request (com o model do usuário) —
  custo de um client por request aceitável; o embedder permanece singleton.
- Modelo `null` → o adapter usa o default do ambiente (`OPENAI_CHAT_MODEL` /
  `DEFAULT_CHAT_MODEL`).
- A migration NÃO remove o índice HNSW (o autogenerate não detecta o
  `CREATE INDEX` raw do pgvector — corrigido manualmente).