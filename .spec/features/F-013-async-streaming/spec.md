# F-013 — Concorrência real: SSE e upload async

## Resumo
Endpoints de streaming e upload deixam de segurar threads do pool ociosamente:

- **SSE (RAG)**: `POST /chats/{chat_id}/messages` vira `async def` com
  **async generator**; o `ChatOpenAIAdapter` ganha `astream` (client async do
  langchain-openai) — o stream espera no event loop, não prende thread do pool.
- **Upload**: `POST /chats/{chat_id}/files` vira `async def` com
  `await file.read()` + `run_in_threadpool` para o trecho CPU/blocking
  (pypdf, boto3 MinIO, embeddings) — threads ficam livres durante a espera
  de rede.
- **Singleton**: `RagService`/grafo/`ChatOpenAIAdapter` compartilhados (não
  recriados por request), seguindo o padrão do `get_embedder`.
- Testes com `FakeChatLLM.astream` determinístico (sem gastar tokens).

A **fila de vetorização em background (Celery/Redis)** fica para a **F-015** —
fora do escopo desta feature.

## Histórias de usuário
- U-001 — **Como** usuário, **quero** enviar uma pergunta e receber o SSE com
  latência/consumo de recursos estável mesmo com vários chats simultâneos,
  **para** o servidor não travar com concorrência.
- U-002 — **Como** usuário, **quero** subir arquivos sem que o servidor fique
  preso ao upload em espera de rede, **para** outros requests continuarem.
- U-003 — **Como** dev, **quero** que os testes usem um LLM fake com `astream`
  e que a conversão async não regrida o comportamento (SSE tokens, [DONE],
  erro, persistência).
- U-004 — **Como** dev, **quero** que o `RagService`/adapter/grafo sejam
  singletons reutilizados, **para** não recriar client HTTP/grafo por request.

## Critérios de aceite
> Critérios são registrados mecanicamente (AC-### → story → semântica técnica → dono T-###)
> — edite `criteria.reg` e reflita aqui por legibilidade ponto a ponto.

- AC-001 — [U-001] `ChatOpenAIAdapter` ganha `astream(prompt) -> AsyncIterator[str]`
  usando `ChatOpenAI.astream`; `ChatLLM` (Protocol) ganha `astream` opcional.
- AC-002 — [U-001] `RagService.stream` ganha variante async `astream(...) ->
  AsyncIterator[str]` que executa o grafo LangGraph (`graph.astream`,
  stream_mode="custom") e emite tokens.
- AC-003 — [U-003] `FakeChatLLM.astream` determinístico (mesmos tokens do
  `stream`); testes de SSE usam a versão async.
- AC-004 — [U-001] `POST /chats/{chat_id}/messages` vira `async def` +
  `async generator` no `StreamingResponse`; mantém: cria user, emite
  `data: token`, `data: {"message_id"}`, `data: "[DONE]"` e `event: error`
  sem salvar assistant.
- AC-005 — [U-002] `POST /chats/{chat_id}/files` vira `async def`;
  `await file.read()` e `run_in_threadpool` para vetorização (pypdf, boto3,
  embedding e insert); mantém 413/422/200 e `chunk_ids`/`vector_reference`.
- AC-006 — [U-004] Singleton: `ChatOpenAIAdapter`/`Embedder` compartilhados entre
  requests (evita recriar client HTTP por request); `RagService`/retriever
  criados por request (session do SQLAlchemy é por-request); reset nos testes.
- AC-007 — [U-003] Testes: suíte completa verde; teste de concorrência leve
  (ex.: N perguntas em paralelo com fake, SSE íntegro por request).

## Suposições (status: aberto|confirmada|rejeitada)
- A-001 — SSE e upload em `async def` (sem fila nesta feature). — confirmada
- A-002 — Upload usa `await file.read()` + `run_in_threadpool` (boto3/pypdf sync). — confirmada
- A-003 — `ChatOpenAIAdapter.astream` (client async do langchain/openai). — confirmada
- A-004 — `RagService`/adapter/grafo como singletons reutilizados. — confirmada
- A-005 — Fila/background (Celery/Redis) fica para a F-015. — confirmada

## Perguntas em aberto
- (nenhuma)