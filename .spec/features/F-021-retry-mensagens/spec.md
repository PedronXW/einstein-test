# F-021 — Retry no RAG/LLM (mensagens)

## Resumo
No fluxo de mensagens (`POST /messages` → RAG via spillway), falhas
**transientes** do LLM/embeddings (timeout, 5xx, 429, ConnectionError) podem
ser re-tentadas com **backoff limitado (tenacity)** **antes do primeiro token
SSE** — um retry após o streaming ter iniciado faria duplicar tokens já
emitidos. A busca de embeddings (para os chunks) também ganha retry transiente.
Após esgotar as tentativas, mantém o comportamento atual: `event: error` sem
salvar assistant.

## Histórias de usuário
- U-001 — **Como** usuário, **quero** que falhas transitórias do LLM durante a
  resposta sejam tentadas de novo (antes de começar o streaming), **para**
  não receber um erro por uma instabilidade momentânea.
- U-002 — **Como** dev, **quero** que o retry seja **antes do primeiro token**
  (nunca refazer o stream), **para** não duplicar tokens/repetir resposta.
- U-003 — **Como** dev, **quero** que as embeddings usadas na busca também
  tenham retry transiente, **para** o RAG não falhar por timeout do provedor.
- U-004 — **Como** dev, **quero** configuração via env (`LLM_MAX_RETRIES`,
  `LLM_RETRY_BACKOFF`) com log estruturado do retry, **para** operar/monitorar.

## Critérios de aceite
> Critérios são registrados mecanicamente (AC-### → story → semântica técnica → dono T-###)
> — edite `criteria.reg` e reflita aqui por legibilidade ponto a ponto.

- AC-001 — [U-001/U-002] `ChatOpenAIAdapter.astream` aplica retry transiente
  apenas na **aquisição** do primeiro chunk: se a chamada inicial falhar (antes
  de qualquer token), re-tenta com backoff (`tenacity retry_if_exception_type`
  de transient + `wait_exponential`); após o primeiro token, NÃO re-tenta.
- AC-002 — [U-002] `ChatOpenAIAdapter.stream` (sync) tem o mesmo comportamento
  de retry transiente no primeiro chunk (compatibilidade com testes F-011).
- AC-003 — [U-003] `_embed_question`/retrieve (embeddings) aplica retry
  transiente (sem afetar o streaming de resposta).
- AC-004 — [U-004] Config via env `LLM_MAX_RETRIES` (default 2),
  `LLM_RETRY_BACKOFF` (default 1s, `wait_exponential`); logs estruturados do
  retry (event `llm_retry`, attempt).
- AC-005 — [U-001] Testes: LLM fake que falha 1× no início e depois responde →
  astream produz os tokens; LLM que falha sempre → exceção `event: error` sem
  assistant; fake que emite 1 token e depois falha → NÃO re-tenta (stream não
  refeito); retry transiente só para as exceções esperadas.

## Suposições (status: aberto|confirmada|rejeitada)
- A-001 — Retry limitado (tenacity) apenas no primeiro token (antes do stream). — confirmada
- A-002 — Embeddings também com retry transiente. — confirmada
- A-003 — Config via env (`LLM_MAX_RETRIES`, `LLM_RETRY_BACKOFF`). — confirmada
- A-004 — Após esgotar, comportamento atual (`event: error` sem salvar). — confirmada

## Perguntas em aberto
- (nenhuma)