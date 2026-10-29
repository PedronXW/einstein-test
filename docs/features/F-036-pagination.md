# F-036 — Paginação nos endpoints de listagem

## O que foi feito
Paginação **padronizada** nos três endpoints de listagem (`GET /chats`,
`GET /chats/{id}/messages`, `GET /chats/{id}/files`) com envelope
`{items, page, page_size, total, total_pages}`, parâmetros `page`/`page_size`
(default `20`, máximo `100`, validação 422) e **usos internos intactos**:
histórico do RAG (`list_messages`) e `files_state`/`rag_readiness` continuam
recebendo a lista completa.

### Envelope paginado (AC-004)
- `items` — elementos da página; `page`/`page_size` — eco dos parâmetros;
  `total` — total de registros; `total_pages = ceil(total / page_size)`.
- Defaults: `page=1`, `page_size=20`. Página além do fim → `items: []` com
  `total` real.
- Política (default/máx/mín) mora em `services/pagination.py` (fonte única,
  fora do controller — aderente ao layering F-031).

### Repositórios e serviços (AC-006)
- `list()` dos repositórios (`Chat`/`Message`/`File`) ganha `limit`/`offset`
  **opcionais** (default = lista completa) + `count()`.
- Serviços ganham `list_*_page(...) -> (items, total)`; `list_*` original sem
  paginação segue para os usos internos (histórico RAG, `files_state`).

### Contrato (breaking, aceito)
- `GET /chats`, `GET /chats/{id}/messages` e `GET /chats/{id}/files` agora
  retornam envelope em vez de lista — testes existentes atualizados para
  consumir `body["items"]`.

## Critérios de aceite implementados

| AC | História | Status | Prova |
|----|----------|--------|-------|
| AC-001 | U-001 — `GET /chats` paginado (envelope, `created_at desc`) | PASS | `tests/api/test_pagination.py -k 'ac001'` |
| AC-002 | U-002 — `GET /chats/{id}/messages` paginado (ordem asc estável) | PASS | `tests/api/test_pagination.py -k 'ac002'` |
| AC-003 | U-003 — `GET /chats/{id}/files` paginado (`created_at desc`) | PASS | `tests/api/test_pagination.py -k 'ac003'` |
| AC-004 | U-004 — defaults page=1/page_size=20, total_pages, página além do fim | PASS | `tests/api/test_pagination.py -k 'ac004'` |
| AC-005 | U-005 — page<1, page_size<1 ou page_size>100 → 422 | PASS | `tests/api/test_pagination.py -k 'ac005'` |
| AC-006 | U-006 — repos/serviços com limit/offset opcionais + count; internos intactos | PASS | `tests/services/test_pagination.py -k 'ac006'` |

## Veredito mecânico
`specs proof F-036-pagination` → `PASS` (6/6 ACs).
`uv run pytest -m "not integration"` → `434 passed, 1 deselected`.
`ruff check .` → all passed.

## Como usar
```bash
GET /chats?page=1&page_size=20
# {
#   "items": [...], "page": 1, "page_size": 20,
#   "total": 42, "total_pages": 3
# }
```
- `page_size` acima de 100 ou `page`/`page_size` < 1 → `422`.
- Mensagens paginadas em ordem cronológica ascendente (página 1 = mais antigas).

## Arquivos
- `src/einstein_test/schemas/page.py` (novo — `Page[T]` genérico + `build`)
- `src/einstein_test/services/pagination.py` (novo — `DEFAULT_PAGE_SIZE`,
  `MAX_PAGE_SIZE`, `MIN_PAGE`)
- `src/einstein_test/repositories/{chat,message,file}.py` (`limit`/`offset`
  opcionais + `count`)
- `src/einstein_test/services/{chat,message,file}.py` (`list_*_page`)
- `src/einstein_test/api/{chats,messages,files}.py` (envelope paginado)
- `tests/api/test_pagination.py` (novo), `tests/services/test_pagination.py`
  (novo) — e testes antigos atualizados para `["items"]`
- `docs/features/F-036-pagination.md` (este)
