# F-023 — Refactor do RAG (fatorar grafos e módulo rag)

## O que foi feito
`services/rag.py` (428 linhas) foi dividido em um **pacote** com submódulos
coesos, sem mudança de comportamento (a suíte permanece verde):

- `services/rag/llm.py` — `ChatLLM` (Protocol), `FakeChatLLM`,
  `ChatOpenAIAdapter` (com retry transiente no primeiro token), constantes e
  `allowed_models()`.
- `services/rag/graph.py` — `RagState`, `build_prompt`, `_retrieve_chunks` e
  o **construtor comum `compile_rag_graph(async_=...)`** que monta o
  `StateGraph` uma única vez (eliminando a duplicação entre `build_graph` e
  `build_graph_async`); o retrieve async usa `asyncio.to_thread`.
- `services/rag/service.py` — `RagService` + factory (`get_rag_service`,
  `set_rag_factory`, `reset_rag_factory`).
- `services/rag/__init__.py` — **re-exporta** a API pública mantida
  (`ChatLLM`, `FakeChatLLM`, `ChatOpenAIAdapter`, `RagService`, `build_graph`,
  `build_graph_async`, `build_prompt`, `get_rag_service`, `set_rag_factory`,
  `reset_rag_factory`, `allowed_models`, `LLM_MAX_RETRIES`,
  `LLM_RETRY_BACKOFF`) — callers e testes existentes **não mudaram**.

## Critérios de aceite implementados

| AC | História | Status | Prova |
|----|----------|--------|-------|
| AC-001 | U-001/U-002 — pacote `services/rag/` com llm.py/graph.py/service.py + construtor comum | PASS | `tests/services/test_rag_refactor.py -k ac001` |
| AC-002 | U-001 — `services/rag.py` re-exporta a API pública; imports intactos | PASS | `tests/services/test_rag_refactor.py -k ac002` |
| AC-003 | U-002 — duplicação da montagem do grafo eliminada (um único StateGraph/compile) | PASS | `tests/services/test_rag_refactor.py -k ac003` |
| AC-004 | U-003 — suíte completa verde (292) + proof das specs de RAG | PASS | `tests/services/test_rag_refactor.py` |

## Veredito mecânico
`specs proof --strict F-023-refactor-rag` → `PASS` (4/4 ACs). `uv run pytest` →
`292 passed`.

## Arquivos
- `src/einstein_test/services/rag/` (novo pacote): `__init__.py`, `llm.py`,
  `graph.py`, `service.py`
- `tests/services/test_rag_refactor.py` (novo)

## Notas
- Refactor **sem mudança de comportamento**: apenas reorganização de módulos e
  remoção da duplicação na montagem do grafo.
- A API pública (`from einstein_test.services.rag import ...`) permanece
  idêntica — nenhum caller/consumidor precisa mudar.