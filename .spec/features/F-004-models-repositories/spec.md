# F-004 — Models Chat, File, Message + repositories

## Resumo
Criar as models SQLAlchemy declarativas **Chat**, **File** e **Message** (Base em
`app/db/base.py`) com seus relacionamentos, e um **repository** para Chat e File
(Protocol + implementação SQLAlchemy), com persistência via SQLAlchemy e testes
contra banco **em memória (SQLite)**. Gerar a **migration Alembic** autogenerate
para as novas tabelas.

## Histórias de usuário
- U-001 — **Como** dev, **quero** models SQLAlchemy `Chat`, `File` e `Message`
  declaradas sobre a `Base`, **para** persistir chats, arquivos e mensagens.
- U-002 — **Como** dev, **quero** `ChatRepository` e `FileRepository`
  (Protocol + impl SQLAlchemy) com operações CRUD básicas, **para** abstrair a
  persistência da lógica de aplicação.
- U-003 — **Como** dev, **quero** testes contra banco SQLite em memória,
  **para** validar models/repos sem depender do postgres do compose.
- U-004 — **Como** dev, **quero** uma migration Alembic autogenerate das novas
  tabelas, **para** o schema convergir no postgres real.

## Critérios de aceite
> Critérios são registrados mecanicamente (AC-### → story → semântica técnica → dono T-###)
> — edite `criteria.reg` e reflita aqui por legibilidade ponto a ponto.

- AC-001 — [U-001] `Chat` declarada em `app/models/chat.py`: `id` (int PK),
  `name`, `description` (nullable), `created_at`, `updated_at`, `deleted_at`,
  relação `messages` → `Message`, relação `files` → `File` (via `chat_id`).
- AC-002 — [U-001] `File` declarada em `app/models/file.py`: `id`, `name`,
  `url`, `type`, `size`, `created_at`, `updated_at`, `deleted_at`, `chat_id` (FK).
- AC-003 — [U-001] `Message` declarada em `app/models/message.py`: `id`,
  `content`, `role` (nullable), `chat_id` (FK), `created_at`, `updated_at`,
  `deleted_at`.
- AC-004 — [U-002] `ChatRepository` e `FileRepository` como Protocol em
  `app/repositories/` com implementação SQLAlchemy (create/get_by_id/list/delete
  soft) injetável por sessão; registrados via `__all__` export.
- AC-005 — [U-003] Testes em `tests/repositories/` usam SQLite `:memory:` com
  `create_all` da Base: criar/listar/buscar/remover chat e file comprovam o CRUD;
  rodam com `uv run pytest` sem postgres.
- AC-006 — [U-004] Migration Alembic gerada (autogenerate) reflete as 3 tabelas
  (`alembic/versions/*.py`) e `alembic upgrade head --sql` (offline) emite os
  `CREATE TABLE`; `alembic/versions/` não está mais vazio.

## Suposições (status: aberto|confirmada|rejeitada)
- A-001 — PK são inteiros (sem UUID) e sem constraints extras além de PKs/FKs. — confirmada
- A-002 — `description` de Chat e `role` de Message são nullable. — confirmada
- A-003 — `File.chat_id` é FK obrigatória (arquivo pertence a um chat). — confirmada
- A-004 — remoção é soft delete (preenche `deleted_at`, não `DELETE` físico). — confirmada
- A-005 — testes usam SQLite `:memory:` + `Base.metadata.create_all`. — confirmada

## Perguntas em aberto
- (nenhuma)