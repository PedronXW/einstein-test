# F-006 — Service e Controller de Messages

## O que foi feito
**MessageRepository** dedicado (Protocol + SQLAlchemy) e **MessageService**
(CRUD orquestrando o repositório), mais os **controllers REST** de messages com
rotas aninhadas `/chats/{chat_id}/messages`, schemas `MessageCreate`/
`MessageRead`, e erros `404` (chat ou message inexistente).

## Critérios de aceite implementados

| AC | História | Status | Prova |
|----|----------|--------|-------|
| AC-001 | U-001 — `MessageRepository` + `MessageRepositorySQLAlchemy` (create/get_by_id/list por chat/delete soft) | PASS | `tests/services/test_message_service.py -k ac001` |
| AC-002 | U-002 — `MessageService` (create/get/list/delete) + `MessageNotFoundError` | PASS | `tests/services/test_message_service.py -k ac002` |
| AC-003 | U-003 — rotas `/chats/{id}/messages` (POST/GET) e `/messages/{id}` (GET/DELETE) | PASS | `tests/api/test_messages.py -k ac003` |
| AC-004 | U-003 — schemas `MessageCreate`/`MessageRead` (content, role, chat_id, timestamps) | PASS | `tests/api/test_messages.py -k ac004` |
| AC-005 | U-003/U-004 — CRUD + 404 (chat inexistente e message inexistente) com detail | PASS | `tests/api/test_messages.py -k ac005` |

## Veredito mecânico
`specs proof --strict F-006-services-messages` → `PASS` (5/5 ACs). `uv run pytest` → `66 passed`.

## Endpoints
- `POST /chats/{chat_id}/messages` — cria message (`content` obrigatório, `role` opcional); 404 se chat inexistente
- `GET /chats/{chat_id}/messages` — lista mensagens do chat (ordem por created_at asc); 404 se chat inexistente
- `GET /messages/{message_id}` — busca por id; 404 se não existe
- `DELETE /messages/{message_id}` — soft delete; 404 se não existe

## Arquivos
- `app/repositories/message.py` (Protocol + impl SQLAlchemy)
- `app/services/message.py` (`MessageService`, `MessageNotFoundError`)
- `app/api/messages.py` (router), `app/schemas/message.py`
- `app/main.py` (registro do router)
- `tests/services/test_message_service.py`, `tests/api/test_messages.py`

## Notas
- `MessageRepository.list(chat_id)` filtra por chat e exclui soft-deleted
  (mensagens isoladas entre chats).
- Soft delete via `deleted_at` (timezone-aware), consistente com F-004/F-005.
- Padrão de controllers/404 idêntico ao F-005 (chats): service levanta
  `ChatNotFoundError`/`MessageNotFoundError`, controller converte em 404 detail.
- Limites de schema: `content` (1..100_000), `role` (≤50), alinhados ao model.

## Ressalva de segurança (registrada no deep review)
Os endpoints de messages **ainda não têm autenticação/owner-scoping** — mesmo
padrão da F-005. Hoje não há dado pessoal/de aluno nos models (Chat/Message sem
dono), e a constituição (C-PRIV/C-AUDIT) passa. O security review classifica
auth + escopo por dono + IDOR (ids sequenciais globais) como **pré-requisito
bloqueante** para qualquer feature futura que anexe owner/dado pessoal a chats
ou messages. Deve ser tratado em feature dedicada de autenticação antes de
expor dados sensíveis.