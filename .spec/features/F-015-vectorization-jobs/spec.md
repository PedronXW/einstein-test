# F-015 — Fila de vetorização em background (Celery/Redis)

## Resumo
A vetorização de arquivos (extração→chunk→embedding→insert) sai do request
HTTP e roda em um **worker Celery** (Redis como broker/result backend). O
upload passa a responder imediatamente com **202** e o `File` ganha
**`status: pending`**; o worker processa e atualiza para **`ready`** (com
`chunk_ids`/`vector_reference`) ou **`error`** (com `error_detail`).
`GET /files/{id}` expõe o andamento.

## Histórias de usuário
- U-001 — **Como** usuário, **quero** subir um arquivo e receber a resposta
  **na hora** (`202 Accepted` com status `pending`), **para** não esperar a
  vetorização no upload.
- U-002 — **Como** usuário, **quero** consultar `GET /files/{id}` e ver o
  `status` (`pending|ready|error`) e, em erro, o `error_detail`, **para**
  saber se o arquivo já pode ser usado nas perguntas do RAG.
- U-003 — **Como** dev, **quero** uma task Celery `vectorize_file(file_id)`
  que baixa o conteúdo do storage, extrai/chunk/embeds/insert e atualiza o
  File, **para** processar em background com retry/erro capturado.
- U-004 — **Como** dev, **quero** Redis no compose e Celery app configurado,
  **para** executar o worker localmente e em produção.

## Critérios de aceite
> Critérios são registrados mecanicamente (AC-### → story → semântica técnica → dono T-###)
> — edite `criteria.reg` e reflita aqui por legibilidade ponto a ponto.

- AC-001 — [U-001] `File` ganha `status` (`pending|ready|error`, default
  `pending`) e `error_detail` (nullable) — migration Alembic. `FileRead`
  expõe ambos.
- AC-002 — [U-001] `POST /chats/{chat_id}/files` enfileira a task Celery e
  retorna **202** com `status=pending` (em vez de bloquear vetorizando). O
  limite 413/422 de upload permanece; a vetorização não roda no request.
- AC-003 — [U-002] `GET /files/{id}` (e lista) refletem o status atualizado
  pelo worker (`ready` com `chunk_ids`, `error` com `error_detail`).
- AC-004 — [U-003] Celery app (`src/einstein_test/tasks/__init__.py`
  `vectorize_file`) recebe `file_id`, baixa o conteúdo do **storage**
  (`Storage.download` novo no Protocol/MinIO/InMemory), vetoriza
  (reutiliza `FileService._vectorize`/fluxo F-010) e atualiza
  `status/error_detail`. Testável sem broker (visor `task_name.apply` direto).
- AC-005 — [U-003] Erro na task → `status=error` + `error_detail`
  (mensagem genérica salva no banco, sem vazar internals ao cliente).
- AC-006 — [U-004] Redis no `docker-compose.yml` (broker/backend do Celery);
  deps `celery` e `redis` no pyproject; app Celery carregável (`celery_app`).
- AC-007 — [U-002/U-003] Testes: upload → 202 pending; worker executa
  vetorização (mock no lugar de enfileirar/broker) → arquivo vira ready com
  chunks; falha → error com detail; ownership preservado.

## Suposições (status: aberto|confirmada|rejeitada)
- A-001 — Upload responde 202 + File(status=pending) e enfileira Celery. — confirmada
- A-002 — Coluna `status` (pending/ready/error) + `error_detail` (nullable). — confirmada
- A-003 — Celery + Redis (broker/backend) no compose; deps `celery`, `redis`. — confirmada
- A-004 — `Storage.download` adicionado (worker baixa o conteúdo). — confirmada
- A-005 — Task `vectorize_file(file_id)` atualiza status; testável sem broker. — confirmada

## Perguntas em aberto
- (nenhuma)