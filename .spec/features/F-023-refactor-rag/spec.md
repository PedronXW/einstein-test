# F-023 — Refactor do RAG (fatorar grafos e módulo rag)

## Resumo
O `services/rag.py` (~428 linhas) mistura Protocol/LLM adapters, retry
tenacity, grafos LangGraph (sync+async duplicados), prompt, service e factory.
Este refactor **não muda comportamento** (suíte permanece verde): separa o
módulo em submódulos coesos (`llm.py`, `graph.py`, `service.py`), fatora a
duplicação dos grafos num construtor comum, e mantém `services/rag.py` como
módulo re-exportador — todos os imports existentes continuam funcionando.

## Histórias de usuário
- U-001 — **Como** dev, **quero** que `services/rag.py` fique mais enxuto,
  **para** legibilidade e manutenção.
- U-002 — **Como** dev, **quero** que os grafos sync e async compartilhem um
  construtor comum (sem duplicação de nós), **para** reduzir risco de drift.
- U-003 — **Como** dev, **quero** que os imports existentes
  (`from einstein_test.services.rag import ...`) continuem funcionando,
  **para** não quebrar callers/tests.

## Critérios de aceite
> Critérios são registrados mecanicamente (AC-### → story → semântica técnica → dono T-###)
> — edite `criteria.reg` e reflita aqui por legibilidade ponto a ponto.

- AC-001 — [U-001/U-002] Novo pacote `services/rag/` com `llm.py`
  (ChatLLM/FakeChatLLM/ChatOpenAIAdapter + retry helpers + constantes e
  `allowed_models`), `graph.py` (RagState, build_prompt, _retrieve_chunks,
  construtor comum de grafo `compile_rag_graph(retrieve, generate)` que gera
  sync E async sem duplicar os nós), e `service.py` (RagService + factory).
- AC-002 — [U-001] `services/rag.py` vira re-exportador: reexporta o `__all__`
  público atual (ChatLLM, FakeChatLLM, ChatOpenAIAdapter, RagService,
  build_graph, build_graph_async, build_prompt, get_rag_service,
  set_rag_factory, reset_rag_factory, allowed_models). Callers e testes não
  mudam.
- AC-003 — [U-002] A duplicação dos nós retrieve/generate entre sync e async é
  eliminada (um único `compile_rag_graph` com `async_=True|False`), com
  `asyncio.to_thread` no retrieve async.
- AC-004 — [U-003] Suíte completa continua verde (288+ testes) e o proof das
  specs de RAG (F-011/F-013/F-021/F-022) permanece PASS.

## Suposições (status: aberto|confirmada|rejeitada)
- A-001 — Refactor sem mudança de comportamento (suíte verde é a prova). — confirmada
- A-002 — `services/rag.py` re-exporta a API pública atual (compat). — confirmada
- A-003 — Grafos sync/async compartilham construtor comum (sem duplicação). — confirmada

## Perguntas em aberto
- (nenhuma)