# tasks — fila Celery (processamento em background)

Vetorização **assíncrona** de arquivos (F-015/F-020): o upload responde `202` e
o worker processa fora do request HTTP.

## Arquivo

- `__init__.py` — `celery_app` (broker/backend Redis) e a task
  `vectorize_file(file_id)`, que delega a orquestração ao
  `FileService.vectorize_uploaded`.

## Comportamento

- Erros **permanentes** (validação/invariante) → `status: error` imediato.
- Falhas **transientes** (storage/LLM/DB) → **retry com backoff exponencial**
  (`VECTORIZE_MAX_RETRIES` / `VECTORIZE_RETRY_BACKOFF`).

## Fluxo

```
upload (HTTP 202) → enfileirar → worker: vectorize_file → FileService
→ extractor → chunker → embedder → file_chunks (ready)
```
