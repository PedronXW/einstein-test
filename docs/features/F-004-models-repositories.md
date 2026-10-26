# F-004 — Models Chat, File, Message + repositories

## O que foi feito
Models SQLAlchemy declarativas **Chat**, **File** e **Message** sobre a `Base`
(`app/db/base.py`), com relacionamentos (Chat.messages, Chat.files, File.chat_id,
Message.chat_id) e timestamps comuns. Repositórios **ChatRepository** e
**FileRepository** como `Protocol` + implementação SQLAlchemy (create/get_by_id/
list/delete soft). Testes contra **SQLite :memory:**. Migration Alembic
**autogenerate** das 3 tabelas criada e aplicada no postgres do compose.

## Critérios de aceite implementados

| AC | História | Status | Prova |
|----|----------|--------|-------|
| AC-001 | U-001 — `Chat` (id, name, description, timestamps, relaç. messages/files) | PASS | `tests/models/test_models.py -k ac001` |
| AC-002 | U-001 — `File` (id, name, url, type, size, timestamps, chat_id FK) | PASS | `tests/models/test_models.py -k ac002` |
| AC-003 | U-001 — `Message` (id, content, role, chat_id FK, timestamps) | PASS | `tests/models/test_models.py -k ac003` |
| AC-004 | U-002 — `ChatRepository`/`FileRepository` Protocol + impl SQLAlchemy | PASS | `tests/repositories/test_repositories.py -k ac004` |
| AC-005 | U-003 — CRUD em SQLite `:memory:` (`create_all`) roda com pytest | PASS | `tests/repositories/test_repositories.py -k ac005` |
| AC-006 | U-004 — migration `e324e7cb8782` cria chats/files/messages; offline SQL emite CREATE TABLE | PASS | `tests/alembic/test_alembic_config.py -k ac006` |

## Veredito mecânico
`specs proof --strict F-004-models-repositories` → `PASS` (6/6 ACs).
Validação viva: `alembic upgrade head` aplicado no postgres do compose
(tabelas `chats`, `files`, `messages` criadas); postgres derrubado após a prova.

## Arquivos
- `app/models/` — `chat.py`, `file.py`, `message.py`, `mixin.py` (timestamps), `__init__.py`
- `app/repositories/` — `chat.py`, `file.py` (Protocol + impl), `sqlalchemy.py` (reexports), `__init__.py`
- `alembic/versions/e324e7cb8782_create_chats_files_messages.py`
- `tests/models/test_models.py`, `tests/repositories/test_repositories.py`

## Notas
- Soft delete: `delete()` preenche `deleted_at` (UTC, timezone-aware); busca/lista
  filtram `deleted_at IS NULL`.
- `alembic/env.py` agora importa `app.models` para que o autogenerate enxergue as models.
- A prova AC-005 da F-002 evoluiu: a `Base` deixou de estar vazia e agora registra
  as 3 tabelas (expected, pois a F-004 adiciona modelos).