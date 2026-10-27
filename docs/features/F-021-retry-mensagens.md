# F-021 — Retry no RAG/LLM (mensagens)

## O que foi feito
Falhas **transientes** do LLM/embeddings no fluxo RAG (`POST /messages`) agora
são re-tentadas com **backoff exponencial (tenacity)** — **apenas antes do
primeiro token SSE** (nunca refaz o stream, evitando duplicar tokens já
emitidos).

- `ChatOpenAIAdapter.astream`/`stream`: protegem a **aquisição do primeiro
  chunk** com retry (re-invocando o stream); após o 1º token, o restante é
  consumido sem retry.
- `RagService._embed_question`: embeddings da pergunta com retry transiente
  (não afeta o streaming da resposta).
- Exceções transientes: `ConnectionError`, `TimeoutError`, `OSError`
  (rede/storage/provedor temporário). Outras exceções propagam imediatamente.
- Após esgotar `LLM_MAX_RETRIES`, o fluxo mantém o comportamento atual:
  `event: error` sem salvar assistant.

## Critérios de aceite implementados

| AC | História | Status | Prova |
|----|----------|--------|-------|
| AC-001 | U-001/U-002 — `astream` re-tenta transiente no 1º chunk (tenacity, backoff) | PASS | `tests/services/test_retry_mensagens.py -k ac001` |
| AC-002 | U-002 — `stream` (sync) mesmo comportamento (compat F-011) | PASS | `tests/services/test_retry_mensagens.py -k ac002` |
| AC-003 | U-003 — `_embed_question` com retry transiente | PASS | `tests/services/test_retry_mensagens.py -k ac003` |
| AC-004 | U-004 — `LLM_MAX_RETRIES`/`LLM_RETRY_BACKOFF` via env; logs estruturados do retry | PASS | `tests/services/test_retry_mensagens.py -k ac004` |
| AC-005 | U-001 — fake falha 1×→tokens; sempre falha→RetryError; após 1 token não re-tenta; só transientes | PASS | `tests/services/test_retry_mensagens.py -k ac005` |

## Veredito mecânico
`specs proof --strict F-021-retry-mensagens` → `PASS` (5/5 ACs). `uv run pytest` →
`276 passed`.

## Configuração
- `LLM_MAX_RETRIES` (default 2), `LLM_RETRY_BACKOFF` (default 1s, base do
  `wait_exponential`). Documentadas em `.env.example`.

## Arquivos
- `src/einstein_test/services/rag.py` — retry no `ChatOpenAIAdapter`
  (`astream`/`stream` com proteção do 1º chunk) + `RagService._embed_question`;
  constantes `LLM_MAX_RETRIES`/`LLM_RETRY_BACKOFF`; helpers `_is_transient`,
  `_retrying`, `_retrying_sync`.
- `.env.example` — variáveis de retry do LLM.
- `tests/services/test_retry_mensagens.py` (novo)

## Notas
- O retry só acontece **antes** do streaming: se o cliente já recebeu o 1º
  token, uma falha posterior não re-tenta (evita resposta duplicada).
- O `RagService` não cria instância de retry por request hot path (usa os
  mesmos `AsyncRetrying`/`Retrying` configurados).
- `reraise=True` garante que, esgotadas as tentativas, a exceção transiente
  original propaga (capturada no `_stream` do endpoint → `event: error`).