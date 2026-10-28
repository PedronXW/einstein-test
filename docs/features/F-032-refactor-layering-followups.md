# F-032 — Refactor layering follow-ups

## O que foi feito
Refactor 100% estrutural (mesmos endpoints, status, schemas e dados) para
fechar os dois resíduos de layering encontrados na auditoria geral pós-F-031,
mantendo a regra de ouro `controller -> service -> repository -> model`.

- **Domínio fora do controller**:
  - `MAX_HISTORY = 10` (política de histórico do RAG) saiu de `api/messages.py`
    para `services/message.py` — `MessageService.MAX_HISTORY` agora é a fonte
    única; o controller apenas importa a constante do service.
  - `tests/api/test_layering_rule.py` passou a rejeitar `MAX_HISTORY =` no
    controller (a prova estrutural de F-031 só cobria `MAX_UPLOAD_SIZE`/
    `MAX_FILES_PER_BATCH`/`DEFAULT_USER_MODEL`/`FILE_STATUS_*`).
- **Infra sem dependência da camada api**:
  - `create_access_token`/`decode_token` (JWT) moveram para `einstein_test.security`
    (mesma moradia do bcrypt), junto com `ALGORITHM`/`DEFAULT_EXPIRE_MINUTES`
    e o cache de secret/expiração.
  - `api/auth.py` reutiliza os helpers de `security` (contrato do
    `get_current_user` preservado; `auth_router` continua importando de
    `api.auth`, que re-exporta).
  - `middleware/rate_limit.py` e `middleware/logging_middleware.py` passam a
    importar `decode_token` de `security`, nunca de `einstein_test.api` —
    elimina a dependência reversa infra→api (mesma linha da AC-006 da F-031).

## Deep review (F4)
Ver `reviews/` e veredito gravado via `specs review`. Achados corrigidos antes
do fechamento da feature.

## Critérios de aceite implementados

| AC | História | Status | Prova |
|----|----------|--------|-------|
| AC-001 | U-001 — `MAX_HISTORY` fonte única em service; controller importa; proof rejeita no controller | PASS | `tests/api/test_layering_rule.py` + `tests/api/test_layering_followups.py` (AC-001) |
| AC-002 | U-002 — JWT em `security`; `api/auth` reutiliza; middleware importa de `security`, não de `api` | PASS | `tests/api/test_layering_followups.py` + `tests/api/test_auth_units.py` (AC-002) |

## Veredito mecânico
`specs proof F-032-refactor-layering-followups` → `PASS` (2/2 ACs).
`uv run pytest` → `383 passed, 1 deselected` (teste que exige MinIO local
pré-existente). `ruff check .` → all passed. `constitution scan` → ok.

## Arquivos
- `src/einstein_test/security.py` (`create_access_token`/`decode_token`,
  `ALGORITHM`, `DEFAULT_EXPIRE_MINUTES`, cache de secret/expiração)
- `src/einstein_test/api/auth.py` (reutiliza JWT de `security`; `__all__` com
  re-export para compat de `auth_router`)
- `src/einstein_test/api/messages.py` (`MAX_HISTORY` importado de service)
- `src/einstein_test/services/message.py` (`MAX_HISTORY = 10`, fonte única)
- `src/einstein_test/middleware/rate_limit.py`,
  `src/einstein_test/middleware/logging_middleware.py`
  (importam `decode_token` de `security`, nunca de `api`)
- `tests/api/test_layering_rule.py` (prova rejeita `MAX_HISTORY =` no controller)
- `tests/api/test_layering_followups.py` (novo — provas estruturais AC-001/AC-002)
- `tests/api/test_auth_units.py` (imports JWT de `security`)