# F-011 — RAG com LangGraph (perguntas sobre arquivos do chat)

## O que foi feito
Perguntas enviadas no chat (`POST /chats/{chat_id}/messages`) agora são
respondidas por um **RAG**: ao criar a message user, o endpoint busca os chunks
mais similares na coleção vetorial do chat (pgvector, **top_k=4**, cosine
distance), monta o contexto com **chunks + pergunta + histórico** do chat e usa
**LangGraph** (`StateGraph` retrieve→generate) com **langchain-openai
`ChatOpenAI`** (modelo `azure/gpt-5-mini`, mesmo `OPENAI_BASE_URL` do `.env` —
spillway) para gerar a resposta. O streaming é entregue via **SSE**
(`text/event-stream`) **token por token** e a resposta é salva como Message
**role=assistant**; falha do LLM → **evento `error` sem salvar**. Testes não
gastam tokens (LLM fake injetável).

## Critérios de aceite implementados

| AC | História | Status | Prova |
|----|----------|--------|-------|
| AC-001 | U-002 — `VectorRepository.search_similar(embedding, chat_id, top_k=4)` (pgvector cosine `<=>` + fallback Python no SQLite) | PASS | `tests/vector/test_search_similar.py` |
| AC-002 | U-003 — deps `langgraph`+`langchain-openai`; `RagService.build_graph` (StateGraph retrieve→generate via ChatOpenAI) | PASS | `tests/services/test_rag_service.py -k ac002` |
| AC-003 | U-003/U-005 — `ChatLLM` Protocol + `FakeChatLLM` determinístico + `ChatOpenAIAdapter` (azure/gpt-5-mini, base_url do `.env`) | PASS | `tests/services/test_rag_service.py -k ac003` |
| AC-004 | U-001/U-004 — `POST /messages` retorna SSE: cria user, executa grafo, emite `data: token` e `data: [DONE]` com id da resposta salva role=assistant | PASS | `tests/api/test_message_rag.py -k ac004` |
| AC-005 | U-001/U-004 — erro do LLM → `event: error` sem salvar assistant; user permanece | PASS | `tests/api/test_message_rag.py -k ac005` |
| AC-006 | U-003 — contexto do generate: chunks + pergunta + histórico; top_k=4 | PASS | `tests/services/test_rag_service.py -k 'ac006 or _build_prompt or _generate_answer'` |
| AC-007 | U-005 — testes API com LLM fake (SSE, DONE, persistência, erro sem salvar) | PASS | `tests/api/test_message_rag.py` |
| AC-008 | U-001 — documentação do streaming SSE | PASS | `tests/api/test_message_rag.py` + `tests/services/test_rag_service.py` + `tests/vector/test_search_similar.py` |

## Veredito mecânico
`specs proof --strict F-011-rag-langgraph` → `PASS` (8/8 ACs). `uv run pytest` → `166 passed`.

## Correções do deep review
- `RagService.stream` usa o grafo LangGraph como **fonte única**: o node
  `generate` emite cada token via `StreamWriter` (`stream_mode="custom"`),
  eliminando a duplicação de embed/busca/LLM (1 de cada por request).
- SSE JSON-encoded (`data: {"message_id": id}` e `data: "[DONE]"`); `[DONE]`
  é o **último** evento, depois do `message_id`.
- Erro do LLM: `logger.exception` no servidor + `event: error` com mensagem
  genérica (sem vazar `str(exc)`).
- Histórico limitado a `MAX_HISTORY=10` mensagens no prompt (evita prompt
  gigante/custo).
- `role` do usuário fixada em `"user"` (não aceita forja de assistant/system).
- `ChatLLM` agora é `typing.Protocol` de verdade; `TOP_K` como constante.
- `_FakeVectorRepository` do teste F-010 ganhou `search_similar` (Protocol).

## Breaking change
- `POST /chats/{chat_id}/messages` deixa de retornar `MessageRead` (JSON) e
  passa a retornar **`text/event-stream`** (SSE) — contrato alterado em relação
  ao F-006. Cada POST persiste 2 linhas: message user + message assistant.
  Consumidores que faziam `.json()` nesse endpoint precisam ler o SSE.

## Streaming SSE
Cliente envia `POST /chats/{chat_id}/messages` com `Accept: text/event-stream`
e corpo JSON `{"content": "<pergunta>"}`. A resposta é um stream
(JSON-encoded por evento):
- `data: "<token>"\n\n` — um evento por token gerado pelo LLM
- `data: {"message_id": <id>}\n\n` — id da resposta salva como role=assistant
- `data: "[DONE]"\n\n` — último evento, fim do stream
- Em falha: `event: error\ndata: {"error": "..."}\n\n` (nenhuma assistant salva)

## Arquivos
- `src/einstein_test/vector/similarity.py` — cosine (Python, testes SQLite)
- `src/einstein_test/vector/repository.py` — `search_similar` (pgvector `<=>` +
  fallback SQLite por chat)
- `src/einstein_test/services/rag.py` — `ChatLLM`/`FakeChatLLM`/
  `ChatOpenAIAdapter`, `RagService`, `build_graph` (LangGraph), factory global
- `src/einstein_test/api/messages.py` — `POST /messages` → SSE streaming
- `.env.example` — `OPENAI_CHAT_MODEL=azure/gpt-5-mini`
- `tests/vector/test_search_similar.py`, `tests/services/test_rag_service.py`,
  `tests/api/test_message_rag.py` (novos) e `tests/api/test_messages.py` (adaptado)

## Notas
- Os testes usam `FakeChatLLM` + `FakeEmbedder` (sem tokens/rede).
- A busca `search_similar` usa `<=>` no PostgreSQL e fallback em Python no
  SQLite (testes) — o operador `<=>` não existe no SQLite.
- `OPENAI_CHAT_MODEL` controla o modelo de chat; `OPENAI_BASE_URL` (spillway)
  é compartilhado com o embedder.