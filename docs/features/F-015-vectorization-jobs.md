# F-015 — Fila de vetorização em background (Celery/Redis)

## O que foi feito
A vetorização de arquivos (extração→chunk→embedding→insert) **saiu do request**
e roda em um **worker Celery** (broker/backend **Redis**). O upload agora
responde **`202 Accepted`** com o `File` em `status=pending` e enfileira a task
`vectorize_file(file_id)`. O worker baixa o conteúdo do storage, vetoriza e
atualiza o `File` para **`ready`** (com `chunk_ids`/`vector_reference`) ou
**`error`** (com `error_detail`). `GET /files/{id}` expõe o andamento.

## Critérios de aceite implementados

| AC | História | Status | Prova |
|----|----------|--------|-------|
| AC-001 | U-001 — `File.status` (pending/ready/error) + `error_detail` (nullable) — migration; `FileRead` expõe | PASS | `tests/models/test_file_status.py` |
| AC-002 | U-001 — `POST /files` retorna 202 com status=pending e enfileira a task | PASS | `tests/api/test_file_jobs.py -k ac002` |
| AC-003 | U-002 — `GET /files/{id}`/lista refletem status do worker | PASS | `tests/api/test_file_jobs.py -k ac003` |
| AC-004 | U-003 — Celery `vectorize_file(file_id)`: baixa do storage (`Storage.download` novo), vetoriza, atualiza ready — testável sem broker | PASS | `tests/tasks/test_vectorize_task.py -k ac004` |
| AC-005 | U-003 — erro na task → `status=error` + `error_detail` (sem vazar internals) | PASS | `tests/tasks/test_vectorize_task.py -k ac005` |
| AC-006 | U-004 — Redis no compose; deps `celery`+`redis`; `celery_app` carregável | PASS | `tests/tasks/test_vectorize_task.py` + `tests/infra/test_celery_app.py` |
| AC-007 | U-002/U-003 — testes upload 202/pending, worker→ready/error, ownership | PASS | `tests/api/test_file_jobs.py` + `tests/tasks/test_vectorize_task.py` |

## Veredito mecânico
`specs proof --strict F-015-vectorization-jobs` → `PASS` (7/7 ACs).
`uv run pytest` → `236 passed`.

## Mudanças na API
- `POST /chats/{chat_id}/files` → **`202 Accepted`** (antes 200 síncrono) com
  `File(status=pending)`; a vetorização acontece em background.
- `FileRead` ganhou `status` (`pending|ready|error`) e `error_detail`.

## Como rodar o worker
```bash
docker compose up -d redis
uv run celery -A einstein_test.tasks worker --loglevel=info
```

## Arquivos
- `src/einstein_test/tasks/__init__.py` — `celery_app` + task `vectorize_file`
- `src/einstein_test/models/file.py` (`+status`, `+error_detail`),
  `schemas/file.py` (`FileRead`)
- `src/einstein_test/storage/minio.py`/`inmemory.py` (`Storage.download`)
- `src/einstein_test/api/files.py` (upload 202 + enqueue)
- `alembic/versions/59f444c4518a_file_status_error_detail_vectorization_.py`
- `docker-compose.yml` (`redis`), `.env.example` (`CELERY_*`),
  `pyproject.toml` (`celery`, `redis`)
- `tests/…` (`test_file_status.py`, `test_celery_app.py`,
  `test_vectorize_task.py`, `test_file_jobs.py` e adaptados)

## Correções do deep review
- **`enqueue_vectorization` resiliente**: se o broker estiver fora, o upload
  retorna 202 mesmo assim (status=pending) e a falha é registrada no log — sem
  orphan de 500 após persistir.
- **Mock central da fila**: `conftest._mock_enqueue` (autouse) substitui a fila
  em todos os testes de API via `enqueue_spy` — nenhum teste depende de Redis
  vivo (antes faltava em `test_files.py`).
- **Task refatorada**: removido o `engine.connect()` morto (só a `Session`
  fica); guard de idempotência (`status == ready` retorna sem reprocessar);
  `error_detail` é apenas o nome da classe (sem vazar mensagens internas).
- **Migration com backfill**: arquivos previamente vetorizados (F-010) viram
  `ready` na migração — não ficam `pending` para sempre.
- **Testes novos**: `error_detail == "RuntimeError"` (pinado), `url inválida`,
  contrato do retorno da task (`status`/`chunks`), idempotência (2ª execução
  não duplica chunks), e `enqueue_spy` validando a tarefa enfileirada.

## Notas
- A task usa sua própria sessão/engine (`create_engine_from_config`) — adequado
  para worker. Nos testes, o engine sqlite é mockado via
  `dependencies.create_engine_from_config`.
- `Storage.download` hoje carrega tudo em memória (ok para o limite 50MB);
  upload de arquivos muito grandes pode exigir streaming no futuro.
- `enqueue_vectorization` é mockável nos testes (captura ids em vez de Celery).