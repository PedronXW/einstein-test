# F-012 — Autenticação JWT + isolamento por usuário

## O que foi feito
A aplicação agora tem **usuários** e **autenticação JWT**:

- `POST /users` registra um usuário (email + senha com **hash bcrypt**);
  `POST /auth/login` valida credenciais e devolve um **JWT**
  (`access_token`, `token_type: bearer`).
- Todos os endpoints de **chats**, **messages** e **files** exigem
  `Authorization: Bearer <token>` via a dependência reutilizável
  `get_current_user`.
- **Isolamento por dono**: cada chat tem `user_id` (owner); listar/consultar/
  deletar um chat e acessar messages/files dele só é permitido ao **dono**
  — chats alheios retornam **404** (não vaza existência). Messages e files
  herdam o isolamento via `chat.user_id`.

## Critérios de aceite implementados

| AC | História | Status | Prova |
|----|----------|--------|-------|
| AC-001 | U-001 — `User` model (email único, password_hash) + `RepositoryUser` + migration; deps `bcrypt`+`pyjwt` | PASS | `tests/models/test_user_models.py` |
| AC-002 | U-001 — `POST /users` (bcrypt, 409 duplicado) e `POST /auth/login` (JWT) | PASS | `tests/api/test_auth.py -k ac002` + `tests/api/test_auth_units.py` |
| AC-003 | U-003 — `get_current_user`/`create_access_token`/`decode_token` (JWT_SECRET, expire 60min) | PASS | `tests/api/test_auth_units.py` |
| AC-004 | U-002 — `Chat.user_id` + migration; `ChatService`/repo escopados por dono | PASS | `tests/models/test_user_models.py` + `tests/api/test_auth.py` |
| AC-005 | U-002 — routers de chats exigem auth; list/get/delete só do dono; alheio → 404 | PASS | `tests/api/test_auth.py -k 'ac005 or owner or requires_auth'` |
| AC-006 | U-004 — routers de files/messages exigem auth + `_ensure_chat_owned` | PASS | `tests/api/test_auth.py -k ac006` |
| AC-007 | U-005 — testes de API com fixture autenticado; isolamento entre 2 usuários; existentes adaptados | PASS | `tests/api/test_auth.py` |
| AC-008 | U-001 — login inválido → 401 sem detalhar | PASS | `tests/api/test_auth.py -k 'ac008 or ac002 or login'` |

## Veredito mecânico
`specs proof --strict F-012-auth-users` → `PASS` (8/8 ACs). `uv run pytest` →
`195 passed`.

## Mudanças na API
- **Novos**:
  - `POST /users` `{email, password}` → `201 UserRead` / `409` duplicado
  - `POST /auth/login` `{email, password}` → `{access_token, token_type: bearer}`
- **Protegidos** (antes públicos): todos os endpoints de chats/messages/files;
  agora exigem `Authorization: Bearer <token>` (401 sem token).
- `POST /chats` passa a retornar **201** (antes 200).

## Configuração
- `.env` / ambiente: `JWT_SECRET` (obrigatório; gere com `openssl rand -hex 32`),
  `ACCESS_TOKEN_EXPIRE_MINUTES` (default 60). Exemplo em `.env.example`.

## Arquivos
- `src/einstein_test/models/user.py` (`User`), `models/chat.py` (`+user_id`,
  `owner` relationship)
- `src/einstein_test/repositories/user.py` (`UserRepository` + bcrypt helpers)
- `src/einstein_test/services/auth.py` (`AuthService`)
- `src/einstein_test/api/auth.py` (JWT + `get_current_user`),
  `api/auth_router.py` (`/users`, `/auth/login`)
- `src/einstein_test/api/chats.py`, `api/messages.py`, `api/files.py`
  (protegidos + ownership)
- `src/einstein_test/schemas/user.py` (`UserCreate`, `UserLogin`, `UserRead`,
  `TokenRead`)
- `alembic/versions/19fe2de00ba7_users_chats_user_id_auth.py`
- `tests/…` novos (`test_user_models.py`, `test_auth.py`,
  `test_auth_units.py`) e adaptados (chats/messages/files/rag/search_similar/
  repositories/chat_service)

## Correções do deep review
- **IDOR corrigido**: `GET/DELETE /files/{id}` e `GET/DELETE /messages/{id}`
  agora validam ownership via `chat.user_id` antes de ler/deletar (alheio → 404
  genérico, sem vazar existência). Testes cruzados com 2 usuários adicionados.
- **Backfill da migration**: `chats.user_id` adicionada, chats existentes sem
  dono são atribuídos a um usuário de migração (`sistema@einstein.test`) e a
  coluna vira NOT NULL — nada fica órfão.
- Email normalizado (`strip().lower()`) em registro/login/get_current_user;
  duplicado concorrente → 409 via `IntegrityError`.
- `JWT_SECRET`/expire resolvidos uma única vez (`lru_cache`), sem
  `load_dotenv()` por request.
- Limite de 72 bytes para senha (bcrypt); helpers de teste centralizados no
  `conftest` (`register_and_login`), removendo 6 cópias locais.

## Notas
- `deleted_at` soft-delete preservado; `user_id` adicionado como nullable na
  migration para não quebrar upgrade com dados existentes (o app sempre cria
  com dono).
- Chats/files/messages de outro usuário retornam 404 (mesmo erro do não
  existe) — não vaza existência.