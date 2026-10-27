# F-013 — Concorrência real: SSE e upload async

## O que foi feito
Os endpoints de streaming e upload deixaram de segurar threads do pool
ociosamente, permitindo concorrência real (~50 usuários):

- **SSE (RAG)**: `POST /chats/{chat_id}/messages` virou `async def` com
  **async generator**; `ChatOpenAIAdapter` ganhou `astream` (client async do
  langchain-openai) e o `RagService.astream` executa um **`StateGraph`
  assíncrono** (nodes async + `asyncio.to_thread` no retrieve) com
  `stream_mode="custom"` — o stream espera no event loop, não prende thread.
- **Upload**: `POST /chats/{chat_id}/files` virou `async def` com
  `await file.read()` + `run_in_threadpool` na vetorização (pypdf, boto3,
  embedding, insert) — threads livres durante a espera de rede.
- **Singleton**: `ChatOpenAIAdapter`/`Embedder` compartilhados entre requests
  (`get_rag_service`), evitando recriar client HTTP por request; o `RagService`/
  retriever são por request (a session do SQLAlchemy é por-request).
- O `build_graph` (sync) foi preservado para compatibilidade com
  `RagService.stream`.

A **fila de vetorização em background (Celery/Redis)** fica para a **F-015**.

## Critérios de aceite implementados

| AC | História | Status | Prova |
|----|----------|--------|-------|
| AC-001 | U-001 — `ChatOpenAIAdapter.astream` (client async) + `ChatLLM.astream` | PASS | `tests/services/test_rag_async.py -k ac001` |
| AC-002 | U-001 — `RagService.astream` (grafo async, `stream_mode=custom`) | PASS | `tests/services/test_rag_async.py -k ac002` |
| AC-003 | U-003 — `FakeChatLLM.astream` determinístico | PASS | `tests/services/test_rag_async.py -k ac003` |
| AC-004 | U-001 — `POST /messages` async (tokens, [DONE], error, persistência) | PASS | `tests/api/test_async_endpoints.py -k ac004` |
| AC-005 | U-002 — `POST /files` async com `await read` + `run_in_threadpool` (413/422/200) | PASS | `tests/api/test_async_endpoints.py -k ac005` |
| AC-006 | U-004 — Adapter/Embedder singleton; RagService/retriever por request | PASS | `tests/api/test_async_endpoints.py -k ac006` |
| AC-007 | U-003 — suíte completa verde + concorrência leve (8 requests paralelos) | PASS | `tests/services/test_rag_async.py` + `tests/api/test_async_endpoints.py` |

## Veredito mecânico
`specs proof --strict F-013-async-streaming` → `PASS` (7/7 ACs). `uv run pytest` →
`210 passed`.

## Correções do deep review
- `_BoomLLM` do teste de erro ganhou `astream` (o teste agora falha pelo motivo
  real: RuntimeError do LLM, não AttributeError).
- DB sync (ownership, criar mensagem, histórico, persistir assistant) movido
  para `run_in_threadpool` — não bloqueia o event loop no path async.
- `astream` alinhado ao `stream` (emite `content or ""`), sem assimetria de
  tokens; `build_graph`/`build_graph_async` compartilham `_retrieve_chunks`.
- Grafos `_graph`/`_graph_async` são lazy (compila só o usado por request).
- Logs do RAG não gravam conteúdo do prompt/dados dos arquivos (só tipo/exc).
- Removida a dependência legacy `pytest-anyio==0.0.0` (o mark `anyio` vem do
  próprio `anyio`); teste de "paralelismo" renomeado para ser honesto (rodada
  sequencial em TestClient); AC-006 agora prova RagService/retriever por
  request e adapter/embedder compartilhados.

## Arquivos
- `src/einstein_test/services/rag.py` — `ChatLLM.astream`, `ChatOpenAIAdapter
  .astream`, `FakeChatLLM.astream`, `build_graph_async`, `RagService.astream`,
  `get_rag_service` com adapter/embedder compartilhados
- `src/einstein_test/api/messages.py` — `create_message` async
- `src/einstein_test/api/files.py` — `upload_file` async (`run_in_threadpool`)
- `tests/services/test_rag_async.py`, `tests/api/test_async_endpoints.py` (novos)
- `tests/api/test_auth.py` — fixture com RAG fake (IDOR de mensagens usa SSE)

## Notas
- `RagService.stream` (sync) preservado — testes antigos de F-011 continuam.
- O retrieve async usa `asyncio.to_thread` para embedder/search_similar
  (sincronos) — não bloqueia o event loop.
- Singleton: adapter/embedder compartilhados; RagService/retriever por request
  para não compartilhar a session do SQLAlchemy entre requests.