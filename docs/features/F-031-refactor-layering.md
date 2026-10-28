# F-031 — Refactor layering controller-service-repository-model

## O que foi feito
Refactor 100% estrutural (mesmos endpoints, status, schemas e dados) para
reforçar a regra de ouro `controller -> service -> repository -> model`. Toda
violação crítica/major/minor da auditoria foi corrigida.

- **Auth/User**:
  - Novo `services/user.py` — `UserService` (get_by_email, set_model,
    resolve_model) com `DEFAULT_USER_MODEL` movido do model para o service.
  - `api/auth.py get_current_user` não chama mais `UserRepositorySQLAlchemy`
    direto; passa por `UserService`.
  - `PATCH /users/me` e o fallback de modelo no streaming usam
    `UserService.set_model`/`resolve_model` (allowlist + default no service).
  - `security.py` novo — `hash_password`/`verify_password` (bcrypt) saíram do
    repository; `UserRepositorySQLAlchemy.create(email, password_hash)` persiste
    o hash pronto e o `AuthService` orquestra hash/verify.
- **File/Tasks**:
  - `FileService.vectorize_uploaded(file_id)` e `mark_error(file_id, error)`
    públicos — a orquestração (repo + storage + `_vectorize` + transição de
    status + commit) saiu da task; a task Celery ficou fina.
  - `create_engine_from_config` moveu para `db/engine.py`; `api/dependencies` e
    a task importam de `db` (task não depende mais de `api`).
  - `create_file` valida `MAX_UPLOAD_SIZE` (lança `FileTooLargeError`);
    `create_files_batch` valida `MAX_FILES_PER_BATCH` (constante movida para o
    service); controllers apenas traduzem para 413.
  - `FILE_STATUS_*` saíram do model para `services/file.py`; `vector_reference`
    com geração única (removido default de uuid no model).
- **Vector/RAG**: `search_similar` não tem mais defaults de domínio
  (`chunks_per_file`/`max_chunks` obrigatórios); a política vive em
  `services/rag/graph.py` (`CHUNKS_PER_FILE=2`, `MAX_CHUNKS=12`).
- **Minor**: `repositories/__init__` deixa de re-exportar de `vector/`;
  `repositories/sqlalchemy.py` inclui `UserRepositorySQLAlchemy`; parsing
  `s3://` unificado em `storage.parse_s3_url`; `AuthService.with_session`
  removido (controllers injetam `AuthService(UserRepositorySQLAlchemy(session))`).

## Deep review (F4)
6 subagentes `review-*` sobre o diff; achados corrigidos:
- **Prova da regra de ouro** (major, testes): novo `tests/api/test_layering_rule.py`
  verifica estruturalmente que controllers nunca chamam `*RepositorySQLAlchemy(`
  como método (só DI em construtor de service) e não definem regra de negócio
  (`MAX_UPLOAD_SIZE`/`MAX_FILES_PER_BATCH`/`DEFAULT_USER_MODEL`/`FILE_STATUS_*`).
- **Segurança** (minor): `delete_file` só apaga do bucket da aplicação
  (`loc[0] == self.storage.bucket`), restaurando a defesa em profundidade.
- **Robustez da task** (minor): `_safe_mark_error` embrulha `mark_error` em
  try/except (falha de persistência não derruba a task).
- **Testes reforçados**: `resolve_model` (3 branches) unitário; `search_similar`
  sem defaults verificado também na implementação (não só Protocol);
  `parse_s3_url` boundary (`s3://bucket`/`""`/`None`); repo não importa bcrypt
  (source).

## Critérios de aceite implementados

| AC | História | Status | Prova |
|----|----------|--------|-------|
| AC-001 | U-001 — controller de auth via `UserService` (get_by_email/set_model/resolve_model) | PASS | `tests/services/test_user_service.py -k ac001` |
| AC-002 | U-004 — bcrypt em `security`; repo persiste hash pronto; AuthService orquestra | PASS | `tests/services/test_security.py -k ac002` |
| AC-003 | U-004 — `DEFAULT_USER_MODEL`/`FILE_STATUS_*` expostos por services | PASS | `tests/services/test_layering_domain.py -k ac003` |
| AC-004 | U-002 — limites de upload/lote validados no service; controller traduz 413 | PASS | `tests/services/test_file_limits.py -k ac004` |
| AC-005 | U-002 — `FileService.vectorize_uploaded`/`mark_error` públicos; task fina | PASS | `tests/services/test_file_vectorize_uploaded.py -k ac005` |
| AC-006 | U-003 — engine em `db/engine.py`; task importa de `db`, nunca de `api` | PASS | `tests/services/test_engine_layer.py -k ac006` |
| AC-007 | U-002 — `search_similar` sem defaults; política única em graph | PASS | `tests/services/test_layering_domain.py -k ac007` |
| AC-008 | U-001/U-003 — minors (re-exports, parse_s3_url, sem with_session) | PASS | `tests/services/test_layering_domain.py tests/services/test_layering_minor.py -k ac008` |

## Veredito mecânico
`specs proof --strict F-031-refactor-layering` → `PASS` (8/8 ACs).
`uv run pytest` → `377 passed, 2 deselected` (1 teste exige MinIO local,
pré-existente no main). `ruff check .` → all passed. `constitution scan` → ok.

## Arquivos
- `src/einstein_test/security.py` (novo — hash/verify bcrypt)
- `src/einstein_test/db/engine.py` (novo — `create_engine_from_config`)
- `src/einstein_test/services/user.py` (novo — `UserService`, `DEFAULT_USER_MODEL`)
- `src/einstein_test/services/file.py` (`vectorize_uploaded`, `mark_error`,
  limites, `FILE_STATUS_*`, `MAX_FILES_PER_BATCH`)
- `src/einstein_test/services/auth.py` (sem `with_session`; usa `security`)
- `src/einstein_test/api/auth.py`, `api/auth_router.py`, `api/messages.py`,
  `api/files.py`, `api/dependencies.py` (controllers via service; engine via `db`)
- `src/einstein_test/tasks/__init__.py` (task fina via service; engine de `db`)
- `src/einstein_test/repositories/user.py` (`create(email, password_hash)`)
- `src/einstein_test/repositories/__init__.py` e `repositories/sqlalchemy.py`
- `src/einstein_test/models/user.py`, `models/file.py` (sem constante de negócio)
- `src/einstein_test/vector/repository.py` (`search_similar` sem defaults)
- `src/einstein_test/storage/__init__.py` (`parse_s3_url`)
- `tests/services/test_user_service.py`, `test_security.py`,
  `test_file_limits.py`, `test_file_vectorize_uploaded.py`,
  `test_engine_layer.py`, `test_layering_domain.py`, `test_layering_minor.py`
  (novos) + `tests/api/test_layering_rule.py` (prova da regra de ouro) +
  testes existentes atualizados aos novos contratos
