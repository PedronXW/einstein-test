# F-036 — Paginação nos endpoints de listagem

## Resumo
Hoje os três endpoints de listagem retornam **todas** as linhas de uma vez
(`GET /chats`, `GET /chats/{id}/messages`, `GET /chats/{id}/files`), sem
limite nem forma de navegar por páginas. Esta feature adiciona **paginação
padronizada** nos três endpoints, com envelope `{items, page, page_size,
total, total_pages}`, parâmetros `page`/`page_size` (default `20`, máximo
`100`, validação 422 fora dos limites) e **sem quebrar** os usos internos que
dependem da lista completa (histórico do RAG, `rag_readiness`).

## Histórias de usuário
- U-001 — **Como** usuário, **quero** paginar a listagem de chats, **para**
  navegar quando há muitos chats.
- U-002 — **Como** usuário, **quero** paginar as mensagens de um chat, **para**
  carregar o histórico em blocos em vez de tudo de uma vez.
- U-003 — **Como** usuário, **quero** paginar os arquivos de um chat, **para**
  navegar quando há muitos arquivos.
- U-004 — **Como** consumidor da API, **quero** uma resposta padronizada
  `{items, page, page_size, total, total_pages}`, **para** saber se há mais
  páginas e montar controles de navegação.
- U-005 — **Como** consumidor da API, **quero** parâmetros de paginação
  validados (422 fora dos limites), **para** não fazer chamadas absurdas.
- U-006 — **Como** desenvolvedor, **quero** que os usos internos (histórico do
  RAG, `rag_readiness`) continuem recebendo a lista completa, **para** não
  mudar o comportamento do RAG.

## Critérios de aceite
> Critérios são registrados mecanicamente (AC-### → story → semântica técnica → dono T-###)
> — edite `criteria.reg` e reflita aqui por legibilidade ponto a ponto.

- AC-001 — [U-001] `GET /chats` retorna envelope `{items, page, page_size,
  total, total_pages}` e respeita `page`/`page_size` (chats ordenados por
  `created_at desc`).
- AC-002 — [U-002] `GET /chats/{chat_id}/messages` retorna envelope paginado
  com ordenação ascendente estável (`created_at asc, id asc`).
- AC-003 — [U-003] `GET /chats/{chat_id}/files` retorna envelope paginado
  (ordenados por `created_at desc`).
- AC-004 — [U-004] Defaults `page=1` e `page_size=20`; `total_pages =
  ceil(total / page_size)`; página além do fim → `items` vazio com `total` real.
- AC-005 — [U-005] `page < 1`, `page_size < 1` ou `page_size > 100` → 422.
- AC-006 — [U-006] Repositórios/serviços ganham `limit`/`offset` opcionais +
  `count()`; usos internos (histórico do RAG via `list_messages`, `files_state`
  via `list_files`) continuam recebendo a lista completa (sem paginação).

## Suposições (status: aberto|confirmada|rejeitada)
- A-001 — Ordenação das mensagens mantida **ascendente** (cronológica) para
  paginação estável — confirmada.
- A-002 — Mudança de contrato (lista → envelope) é aceita, mesmo sendo breaking
  — confirmada.
- A-003 — Usos internos seguem sem paginação — confirmada.
- A-004 — `page` é 1-based; página além do fim retorna `items: []` com `total`
  real — confirmada.
- A-005 — Política de paginação (default 20, máx 100, mín 1) mora em
  `services/pagination.py` (fonte única, fora do controller — layering) —
  confirmada.

## Perguntas em aberto
- (nenhuma)
