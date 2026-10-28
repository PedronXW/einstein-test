# F-034 — Validação de RAG/upload + avisos SSE

## Resumo
Revisão das validações do fluxo de mensagens RAG e upload de arquivos. Hoje o
usuário pode perguntar num chat **sem arquivos** e recebe resposta do LLM com
contexto `(vazio)` (alucinação persistida como `assistant`), não há distinção
entre arquivos `pending` (vetorizando) e `error`, e o upload aceita arquivo
vazio, extensão não-suportada e nome duplicado. Esta feature adiciona:

- **Avisos SSE** (`event: notice`) quando o chat não tem arquivos `ready`
  (responde sem chamar o LLM) e quando há arquivos `pending`/`error` junto com
  `ready` (responde com os prontos + aviso).
- **Validações de upload** no service (fonte única, aderente ao layering
  controller→service→repository→model): arquivo vazio (422/failure), extensão
  fora da whitelist (415/failure) e nome duplicado no mesmo chat (409/failure).
- **Pergunta em branco** (só espaços) rejeitada no schema (422).
- **Exclusão**: comportamento atual (soft delete sem cascade) é **mantido** e
  documentado como limitação conhecida — sem mudança de código nesta feature.

## Histórias de usuário
- U-001 — **Como** usuário, **quero** receber um aviso ao perguntar em um chat
  sem arquivos prontos, **para** saber que preciso enviar arquivos em vez de
  receber uma resposta sem contexto.
- U-002 — **Como** usuário, **quero** que o RAG responda usando os arquivos já
  prontos e me avise quando há arquivos ainda processando ou com erro, **para**
  entender a cobertura da resposta.
- U-003 — **Como** usuário, **quero** que uploads inválidos (vazio, extensão
  não permitida, nome duplicado) sejam recusados claramente, **para** não ter
  arquivos `ready` que não indexaram nada ou entradas duplicadas.
- U-004 — **Como** usuário, **quero** que perguntas em branco sejam rejeitadas,
  **para** não poluir o histórico com mensagens vazias.

## Critérios de aceite
> Critérios são registrados mecanicamente (AC-### → story → semântica técnica → dono T-###)
> — edite `criteria.reg` e reflita aqui por legibilidade ponto a ponto.

- AC-001 — [U-001] `POST /chats/{chat_id}/messages` em chat **sem** nenhum
  arquivo `ready`: 200, mensagem do usuário salva, SSE com `event: notice` e
  corpo `{code: "no_ready_files", message: ...}`; o LLM **não** é chamado e
  nenhuma mensagem `assistant` é criada.
- AC-002 — [U-002] chat com arquivos `ready` **e** `pending`/`error`: stream
  normal (LLM com os prontos) **e** um evento `notice` extra informando
  contagens de `processing` e `failed`.
- AC-003 — [U-004] `content` com apenas espaços/whitespace → 422 (validator no
  `MessageCreate`).
- AC-004 — [U-003] upload único de arquivo vazio (0 bytes) → 422; no batch →
  `failures` com `reason: "arquivo vazio"`.
- AC-005 — [U-003] upload de extensão fora da whitelist (`pdf` + `TEXT_EXTENSIONS`
  do `TextExtractor`) → 415 no único; no batch → `failures` por arquivo.
- AC-006 — [U-003] upload de nome duplicado (case-insensitive) num chat com
  arquivo não deletado do mesmo nome → 409 no único; no batch → `failures`.

## Suposições (status: aberto|confirmada|rejeitada)
- A-001 — Evento SSE de aviso usa `event: notice` com corpo
  `{code, message}` — confirmada.
- A-002 — Duplicado de nome = 409 (conflito de recurso); demais validações de
  upload no service com exceções de domínio traduzidas pelo controller — confirmada.
- A-003 — Avisos SSE não são erros: não trocam o status HTTP (200), não salvam
  `assistant` quando não há `ready`, e não bloqueiam quando há pelo menos um
  `ready` — confirmada.
- A-004 — Exclusão: comportamento atual mantido; documentada como limitação
  conhecida (sem mudança de código nesta feature) — confirmada.

## Perguntas em aberto
- Q-001 — Formato do aviso SSE? → `event: notice` + `{code, message}` (resolvida).
- Q-002 — Duplicado: 409 ou 422? → `409` (resolvida).