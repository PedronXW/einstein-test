# F-019 — Logs robustos (JSON estruturado + request_id)

## O que foi feito
Sistema de logging robusto e **estruturado**:

- **`logging_setup.configure_logging()`**: JSON formatter (campos `ts`,
  `level`, `logger`, `msg`, `request_id` e extras como `event`, `chat_id`,
  `file_id`, `latency_ms`, etc.) no STDOUT; `LOG_LEVEL` via env (default INFO).
- **`RequestIdMiddleware`**: gera `request_id` (UUID) por request, propaga via
  **contextvar** a todos os logs daquele request (logging.Filter), retorna o
  header `X-Request-Id`, e emite um **access log** estruturado ao final
  (`method`, `path`, `status`, `latency_ms`, `user_id`, `ip`).
- **Logs nos pontos críticos**: upload enqueue (king), RAG/SSE (chat_id,
  n_tokens, error) e task Celery (file_id, attempt) — **sem conteúdo de
  prompt/arquivo** (política de privacidade preservada).

## Critérios de aceite implementados

| AC | História | Status | Prova |
|----|----------|--------|-------|
| AC-001 | U-001/U-004 — `configure_logging` JSON + `LOG_LEVEL`; chamado no app e no worker | PASS | `tests/infra/test_logging.py -k ac001` |
| AC-002 | U-002 — `RequestIdMiddleware` (X-Request-Id + access log com request_id/status/latency) | PASS | `tests/infra/test_logging.py -k ac002` |
| AC-003 | U-002 — logs do mesmo request carregam `request_id` (Filter + contextvar) | PASS | `tests/infra/test_logging.py -k ac003` |
| AC-004 | U-003 — logs estruturados em enqueue/RAG/task sem vazar prompt/conteúdo | PASS | `tests/infra/test_logging.py -k ac004` |
| AC-005 | U-001 — JSON parseável; `get_logger` funcional | PASS | `tests/infra/test_logging.py -k ac005` |

## Veredito mecânico
`specs proof --strict F-019-logs-robustos` → `PASS` (5/5 ACs). `uv run pytest` →
`265 passed`.

## Arquivos
- `src/einstein_test/logging_setup.py` — `configure_logging`, `get_logger`,
  `JsonFormatter`
- `src/einstein_test/middleware/logging_middleware.py` — `RequestIdMiddleware`,
  `request_id_var`, `current_request_id`, `RequestIdFilter`
- `src/einstein_test/main.py` — `configure_logging()` + middleware registrado
  antes do rate limit
- `src/einstein_test/tasks/__init__.py` — `configure_logging()` no worker
- `src/einstein_test/api/files.py`, `api/messages.py` — logs estruturados
- `tests/infra/test_logging.py` (novo)

## Correções do deep review
- **`RequestIdFilter` no handler, não no logger**: filtros de logger-pai não
  se propagam aos loggers filhos no Python — o filtro foi movido para o
  `StreamHandler` global de `configure_logging`, então **todos** os registros
  da hierarquia `einstein_test.*` carregam o `request_id`.
- **Ordem de middlewares corrigida**: `RequestIdMiddleware` é o **mais externo**
  (adicionado por último no `create_app`) — respostas 429 do rate limit e 500
  agora passam por ele (ganham `X-Request-Id` e access log).
- **Erro não tratado → access log**: exceção em `call_next` ainda registra o
  access log (o status 500 é correlacionável) antes de propagar.
- **Whitelist completa**: adicionados `message_id` e `ip` aos campos
  conhecidos do `JsonFormatter` (antes descartados silenciosamente).
- **SSE**: o `request_id` é capturado no handler de `create_message` e passado
  explicitamente nos logs `rag_done`/`rag_error` do stream (o
  `BaseHTTPMiddleware` retorna a response antes do corpo).
- **Sem efeito colateral em import-time**: `configure_logging()` não roda mais
  no import de `tasks/` (apenas via `get_logger`, idempotente).
- Testes: removido dead code/imports; `test_ac003` prova a propagação real via
  handler com `RequestIdFilter`; `get_logger("tasks")` e nível asseridos.

## Notas
- A propagação do `request_id` usa `contextvars` + `logging.Filter` — funciona
  em endpoints `def`/`async` e dentro de `run_in_threadpool` (o contexto é
  herdado pelas threads do threadpool do Starlette).
- O `JsonFormatter` só serializa os campos conhecidos (evita logar objetos
  arbitrários/segredos via `_asdict`).
- Política: **nunca** loga conteúdo de prompt/arquivos — apenas ids/contagens.