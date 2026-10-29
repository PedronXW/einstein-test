# schemas — contratos de API (Pydantic)

Validação e serialização de **entrada/saída** HTTP e do envelope de paginação.
Camada sem dependências internas (usada por `api` e `services`).

## Arquivos

- `user.py`, `chat.py`, `message.py`, `file.py` — requests/responses por recurso.
- `page.py` — `Page[T]`: envelope padronizado com `{items, page, page_size,
  total, total_pages}` (F-036).

## Fluxo

```
HTTP body → schema (valida) → service → schema (response) → HTTP
```
