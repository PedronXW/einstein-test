# F-022 — Seleção de modelo de análise por usuário

## Resumo
Cada usuário pode escolher qual modelo de LLM usar nas análises/perguntas do
RAG. A escolha fica em uma coluna `model` no `User` (nullable — ausente = usa o
default do ambiente). O usuário consulta/atualiza via `GET /users/me` e
`PATCH /users/me {model}`. Os modelos permitidos são definidos **somente via
env** (`ALLOWED_MODELS`, separados por vírgula; default
`azure/gpt-5-mini,azure/gpt-6-luna`). O RAG cria um `ChatOpenAIAdapter` **por
usuário** com o modelo escolhido (sem o singleton global do LLM; embedder
continua compartilhado).

## Histórias de usuário
- U-001 — **Como** usuário, **quero** escolher qual modelo usar nas minhas
  análises (ex.: `azure/gpt-5-mini` ou `azure/gpt-6-luna`), **para** adequar a
  resposta ao meu caso.
- U-002 — **Como** usuário, **quero** consultar meu modelo atual e alterá-lo,
  **para** controlar a escolha.
- U-003 — **Como** dev, **quero** que a lista de modelos permitidos venha do
  ambiente (`ALLOWED_MODELS`), **para** habilitar/desabilitar sem deploy.
- U-004 — **Como** dev, **quero** que o RAG use o modelo do usuário (não mais o
  singleton global), **para** respeitar a preferência de cada um.

## Critérios de aceite
> Critérios são registrados mecanicamente (AC-### → story → semântica técnica → dono T-###)
> — edite `criteria.reg` e reflita aqui por legibilidade ponto a ponto.

- AC-001 — [U-001] `User.model` (String nullable, default NULL) + migration;
  `UserRead` expõe `model`. Modelo ausente → comportamento default (env).
- AC-002 — [U-002] `GET /users/me` (autenticado) retorna o perfil incluindo
  `model`. `PATCH /users/me {"model": ...}` atualiza; valida contra
  `ALLOWED_MODELS` (env) → inválido 422 (`não suportado`); vazio/null restaura
  default (null).
- AC-003 — [U-003] `ALLOWED_MODELS` lida do env (default
  `azure/gpt-5-mini,azure/gpt-6-luna`); lista exposta numa constante/helper
  (`allowed_models()`); testes com override.
- AC-004 — [U-004] `get_rag_service(retriever, *, model=None)` cria
  `ChatOpenAIAdapter(model=model or default)` por usuário; o singleton global
  do LLM é removido (embedder permanece compartilhado); o `POST /messages`
  passa o `current_user.model` ao RAG.
- AC-005 — [U-002] Testes de API: PATCH inválido → 422; PATCH válido → 200 e
  GET reflete; usuário sem model usa default; RAG chamado com o model do
  usuário (teste com fake que registra o model usado).

## Suposições (status: aberto|confirmada|rejeitada)
- A-001 — Coluna `model` no User (nullable, null = default do env). — confirmada
- A-002 — GET/PATCH /users/me para consultar/atualizar. — confirmada
- A-003 — Modelos permitidos SÓ via env (`ALLOWED_MODELS`). — confirmada
- A-004 — RAG com adapter por usuário (sem singleton global do LLM). — confirmada

## Perguntas em aberto
- (nenhuma)