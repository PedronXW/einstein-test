# F-011 — RAG com LangGraph (perguntas sobre arquivos do chat)

## Resumo
Perguntas enviadas no chat (role=user) são respondidas por um **RAG**: ao criar
uma message user em `POST /chats/{chat_id}/messages`, busca chunks similares
na coleção vetorial do chat (pgvector, **top_k=4**, cosine distance `<=>`),
monta o contexto com **chunks + pergunta + histórico do chat** e usa
**LangGraph** + **langchain-openai `ChatOpenAI`** (modelo `azure/gpt-5-mini`,
mesmo `OPENAI_BASE_URL` do `.env` — spillway) para gerar a resposta via
**streaming SSE** (`text/event-stream`), **token por evento** + `[DONE]` com o
`message_id` da resposta; a resposta é salva como Message **role=assistant**.
Falha do LLM → evento `error` sem salvar. **Testes não gastam tokens** (LLM
fake injetável).

## Histórias de usuário
- U-001 — **Como** usuário da API, **quero** enviar uma pergunta no chat e
  receber a resposta sobre os arquivos daquele chat **em streaming** (SSE),
  **para** ver a resposta enquanto ela é gerada.
- U-002 — **Como** dev, **quero** uma busca vetorial por similaridade no
  pgvector (cosine `<=>`) filtrada por chat, **para** recuperar os chunks
  relevantes de cada pergunta.
- U-003 — **Como** dev, **quero** um grafo **LangGraph** (retrieve → generate)
  usando `ChatOpenAI` (azure/gpt-5-mini via base_url do `.env`), com contexto
  de chunks + pergunta + histórico, **para** montar a resposta RAG.
- U-004 — **Como** dev, **quero** streaming SSE token por token com `[DONE]`
  contendo o `message_id` da resposta salva, **para** o cliente fechar o fluxo.
- U-005 — **Como** dev, **quero** que os testes usem **LLM fake injetável**
  (sem gastar tokens), **para** validar o fluxo RAG sem custo/rede.

## Critérios de aceite
> Critérios são registrados mecanicamente (AC-### → story → semântica técnica → dono T-###)
> — edite `criteria.reg` e reflita aqui por legibilidade ponto a ponto.

- AC-001 — [U-002] `VectorRepository.search_similar(embedding, chat_id,
  top_k=4)` adicionado (Protocol + SQLAlchemy pgvector cosine `<=>` com join
  `File.chat_id`); nos testes SQLite, implementação fake que calcula cosine em
  Python (SQLite não suporta `<=>`).
- AC-002 — [U-003] Dependências `langgraph` e `langchain-openai` adicionadas;
  `RagService` (ou `RagAssistant`) com `build_graph(llm, retriever, history)`:
  StateGraph com nós `retrieve` (busca por similaridade) e `generate`
  (ChatOpenAI azure/gpt-5-mini, base_url/api_key do `.env`).
- AC-003 — [U-003/U-005] `ChatLLM` abstraído (Protocol) com `stream(prompt) ->
  Iterator[str]`; `FakeChatLLM` determinístico nos testes; `ChatOpenAIAdapter`
  real em produção (reutiliza `OPENAI_BASE_URL`/`OPENAI_API_KEY`).
- AC-004 — [U-001/U-004] `POST /chats/{chat_id}/messages` passa a retornar
  `text/event-stream`: recebe a pergunta (JSON), cria a message user, executa o
  grafo e emite um evento `data: <token>` por token; ao final `data: [DONE]`
  seguido do `message_id` da resposta salva como role=assistant.
- AC-005 — [U-001/U-004] Erro do LLM/grafo durante o streaming → evento
  `event: error` com mensagem; **nenhuma** message assistant é salva; a message
  user já criada permanece.
- AC-006 — [U-003] Contexto do generate: chunks recuperados + pergunta atual +
  histórico de messages anteriores do chat (fora a pergunta em curso);
  `top_k=4`.
- AC-007 — [U-005] Testes `tests/api/test_message_rag.py` com TestClient + LLM
  fake: cria pergunta → SSE contém tokens do fake; `[DONE]` com id; resposta
  assistant persistida com role=assistant; erro do fake → `event: error` sem
  salvar assistant.
- AC-008 — [U-001] Documentação do streaming: cliente consome `text/event-stream`
  do `POST /chats/{chat_id}/messages`; formato SSE documentado em
  `docs/features/F-011-rag-langgraph.md`.

## Suposições (status: aberto|confirmada|rejeitada)
- A-001 — Busca por similaridade pgvector (cosine `<=>`), top_k=4, filtrada por chat. — confirmada
- A-002 — `POST /chats/{chat_id}/messages` muda para SSE (breaking do F-006). — confirmada
- A-003 — Ao criar message user, resposta assistant gerada e salva automaticamente. — confirmada
- A-004 — Streaming SSE: token por evento `data:` + `[DONE]` com id; erro → `event: error` sem salvar. — confirmada
- A-005 — Contexto do generate: chunks + pergunta + histórico do chat. — confirmada
- A-006 — LangGraph (StateGraph retrieve→generate) + `langchain-openai` ChatOpenAI. — confirmada
- A-007 — Modelo `azure/gpt-5-mini`, mesmo `OPENAI_BASE_URL` do `.env` (spillway). — confirmada
- A-008 — Testes sem tokens: `ChatLLM` fake injetável; busca fake em SQLite. — confirmada

## Perguntas em aberto
- (nenhuma)