# F-005 — Services e controllers de Chats

## Resumo
Adicionar o **ChatService** (orquestração CRUD sobre o ChatRepository da F-004),
os **controllers REST** de chat em `app/api/chats.py` (CRUD completo) com
**Pydantic schemas** de entrada/saída, e a **dependency** `get_session`
(sessão por request) injetando no service/repository. Erros de chat não
encontrado respondem `404` com JSON detail.

## Histórias de usuário
- U-001 — **Como** dev, **quero** um `ChatService` com `create_chat`, `get_chat`,
  `list_chats`, `delete_chat`, **para** orquestrar/validar a lógica antes de
  persistir via repositório.
- U-002 — **Como** usuário da API, **quero** endpoints REST de chats
  (`POST /chats`, `GET /chats`, `GET /chats/{id}`, `DELETE /chats/{id}`),
  **para** gerenciar chats via HTTP.
- U-003 — **Como** dev, **quero** Pydantic schemas (`ChatCreate`, `ChatRead`)
  e a dependency `get_session`, **para** validar entrada/saída e injetar sessão
  por request de forma idiomática FastAPI.
- U-004 — **Como** usuário da API, **quero** `404` com `{"detail": ...}` ao
  buscar/deletar chat inexistente, **para** tratar erro de forma clara.

## Critérios de aceite
> Critérios são registrados mecanicamente (AC-### → story → semântica técnica → dono T-###)
> — edite `criteria.reg` e reflita aqui por legibilidade ponto a ponto.

- AC-001 — [U-001] `ChatService` em `app/services/chat.py` com `create_chat`,
  `get_chat`, `list_chats`, `delete_chat`, delegando persistência ao
  `ChatRepository` (Protocol) injetado.
- AC-002 — [U-002] Router `app/api/chats.py` com `POST /chats`, `GET /chats`,
  `GET /chats/{id}`, `DELETE /chats/{id}`, registrado no `create_app`
  (app/main.py); usa o ChatService.
- AC-003 — [U-002/U-003] Schemas Pydantic `ChatCreate` (name obrigatório,
  description opcional) e `ChatRead` (id, name, description) em `app/schemas/`;
  retorno modelado.
- AC-004 — [U-003] Dependency `get_session` (YiedSession da SQLAlchemy) em
  `app/db/` cria sessão por request; injetada nos controllers e repassada ao
  service/repository.
- AC-005 — [U-001/U-002] Testes `tests/api/test_chats.py` com `TestClient`
  (SQLite :memory:) cobrem: POST cria e retorna 201/200 com id; GET lista;
  GET/{id} retorna chat; DELETE remove; **GET/DELETE de id inexistente → 404**
  com `{"detail": ...}`.

## Suposições (status: aberto|confirmada|rejeitada)
- A-001 — Controllers são os routers HTTP em `app/api/chats.py`. — confirmada
- A-002 — CRUD completo: POST/GET/GET-by-id/DELETE. — confirmada
- A-003 — Schemas Pydantic `ChatCreate`/`ChatRead`; response_model modelado. — confirmada
- A-004 — Dependency `get_session` (sessão por request) injetada. — confirmada
- A-005 — Chat não encontrado → HTTPException 404 com `{"detail": ...}`. — confirmada

## Perguntas em aberto
- (nenhuma)