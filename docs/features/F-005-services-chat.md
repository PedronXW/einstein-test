# F-005 — Services e controllers de Chats

## O que foi feito
**ChatService** (orquestração CRUD sobre o ChatRepository) + **controllers REST**
em `app/api/chats.py` (CRUD completo) + **Pydantic schemas** (`ChatCreate`,
`ChatRead`) + dependency **`get_session`** (sessão por request). Chat inexistente
→ `404` com `{"detail": ...}`. Rotas registradas no `create_app`.

## Critérios de aceite implementados

| AC | História | Status | Prova |
|----|----------|--------|-------|
| AC-001 | U-001 — `ChatService` (create/get/list/delete) com repo injetado | PASS | `tests/services/test_chat_service.py -k ac001` |
| AC-002 | U-002 — Router `app/api/chats.py` (POST/GET/GET-id/DELETE) registrado no app | PASS | `tests/api/test_chats.py -k ac002` |
| AC-003 | U-002/U-003 — Schemas `ChatCreate`/`ChatRead`, `response_model` modelado | PASS | `tests/api/test_chats.py -k ac003` |
| AC-004 | U-003 — dependency `get_session` (Session por request, factory configurável) | PASS | `tests/services/test_chat_service.py -k ac004` |
| AC-005 | U-001/U-004 — CRUD via TestClient + 404 com detail p/ id inexistente | PASS | `tests/api/test_chats.py -k ac005` |

## Veredito mecânico
`specs proof --strict F-005-services-chat` → `PASS` (5/5 ACs). `uv run pytest` → `51 passed`.
Validação viva (uvicorn + postgres do compose): `POST /chats` → 200 `{"id":1,...}`,
`GET /chats` → lista, `GET /chats/999999` → **404** `{"detail":"chat não encontrado"}`.

## Endpoints
- `POST /chats` — cria chat (`name` obrigatório, `description` opcional)
- `GET /chats` — lista (exclui soft-deleted)
- `GET /chats/{id}` — busca por id; 404 se não existe
- `DELETE /chats/{id}` — soft delete; 404 se não existe

## Arquivos
- `app/services/chat.py` (`ChatService`, `ChatNotFoundError`)
- `app/api/dependencies.py` (`get_session`, `configure_session_factory`)
- `app/api/chats.py` (router)
- `app/schemas/chat.py` (`ChatCreate`, `ChatRead`)
- `tests/services/test_chat_service.py`, `tests/api/test_chats.py`

## Notas
- Session por request via `get_session`; testes usam `configure_session_factory`
  com SQLite `:memory:` (StaticPool p/ compartilhar conexão entre threads).
- `ChatService.get_chat`/`delete_chat` levantam `ChatNotFoundError`, convertida
  em `HTTPException 404` no controller.
- Erros 422 (validação) aparecem ao faltar `name` no POST.