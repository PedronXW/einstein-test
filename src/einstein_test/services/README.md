# services — regras de negócio (camada de aplicação)

Onde mora a **lógica do domínio**: chamam `repositories` para persistir e
`vector`/`storage` para operações auxiliares. Nunca conhecem HTTP.

## Arquivos

- `auth.py` — criação de usuário, login, JWT e senha (bcrypt).
- `chat.py`, `message.py`, `file.py` — regras de cada recurso
  (`FileService.vectorize_uploaded` orquestra a vetorização).
- `user.py` — perfil (ex.: trocar modelo de LLM permitido, F-022).
- `pagination.py` — fonte única dos limites e envelope de paginação (F-036).
- `rag/` — serviço RAG em subpacote coeso (F-023):
  - `llm.py` — Protocol + fakes + adapter OpenAI-compatível com retry (F-021).
  - `graph.py` — grafo LangGraph `retrieve → generate` (sync/async sem duplicação).
  - `service.py` — `RagService` (feed de contexto + histórico + pergunta ao LLM).

## Fluxo

```
service → repositories → models
service → vector (search_similar, embedding)
service → storage (arquivos)
service → rag (geração de resposta)
```

## Fronteiras

- **Pode**: usar `repositories`, `models`, `schemas`, `vector`, `storage`.
- **Não pode**: importar `api` (HTTP). A `tasks` Celery chama o service — o
  service não conhece Celery.
