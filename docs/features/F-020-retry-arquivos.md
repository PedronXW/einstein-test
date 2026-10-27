# F-020 — Retry no processamento de arquivos (Celery)

## O que foi feito
A task `vectorize_file` agora **re-tenta** falhas transientes com **backoff
exponencial** (default `VECTORIZE_MAX_RETRIES=3`, `VECTORIZE_RETRY_BACKOFF=2`),
em vez de marcar `error` na primeira falha:

- **Transientes** (`ConnectionError`, timeout, storage/LLM/DB temporário) →
  `self.retry(exc=exc, countdown=backoff * 2^n)`.
- **Permanentes** (`VectorizationError` — invariants/dimensão/limite; url
  inválida; arquivo ausente) → marca `error` imediatamente, sem retry.
- **Idempotência** preservada: arquivo `ready` não é reprocessado.
- Após esgotar `max_retries` → `status=error` com `error_detail` (nome da
  exceção da última tentativa).

## Critérios de aceite implementados

| AC | História | Status | Prova |
|----|----------|--------|-------|
| AC-001 | U-001 — retry com backoff exponencial + max_retries (env) | PASS | `tests/tasks/test_retry_arquivos.py -k 'ac001 or ac004'` |
| AC-002 | U-002 — erros permanentes sem retry (marcam error) | PASS | `tests/tasks/test_retry_arquivos.py -k ac002` |
| AC-003 | U-003 — idempotência (ready → skip) | PASS | `tests/tasks/test_retry_arquivos.py -k ac003` |
| AC-004 | U-004 — após esgotar, error com error_detail | PASS | `tests/tasks/test_retry_arquivos.py -k 'ac004 or ac001'` |

## Veredito mecânico
`specs proof --strict F-020-retry-arquivos` → `PASS` (4/4 ACs). `uv run pytest` →
`271 passed`.

## Configuração
- `VECTORIZE_MAX_RETRIES` (default 3), `VECTORIZE_RETRY_BACKOFF` (default 2,
  base do backoff exponencial `2^n`). Documentadas em `.env.example`.

## Arquivos
- `src/einstein_test/tasks/__init__.py` — task com retry explícito
  (`bind=True`, `self.retry(countdown=backoff)`) + helper `_mark_error`
- `.env.example` — variáveis de retry
- `tests/tasks/test_retry_arquivos.py` (novo)

## Notas
- Usa retry **explícito** (`self.retry`) em vez de `autoretry_for` para
  permitir: (a) marcar `error` na última tentativa (e não re-levantar), e
  (b) distinguir transiente × permanente no mesmo corpo.
- Erros permanentes retornam `{"status": "error"}` (não re-levantam) — o
  estado fica visível via `GET /files/{id}`.