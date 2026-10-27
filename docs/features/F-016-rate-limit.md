# F-016 — Rate limiting (global e por endpoint)

## O que foi feito
Um middleware global de **rate limiting** protege os endpoints sensíveis (SSE,
upload, login) por **usuário autenticado** ou **IP** (anônimo), com contadores
**em memória** (janela deslizante) — sem dependência externa. Ao exceder o
limite, responde **`429 Too Many Requests`** com cabeçalho `Retry-After`.

## Critérios de aceite implementados

| AC | História | Status | Prova |
|----|----------|--------|-------|
| AC-001 | U-002 — `RateLimitMiddleware` (identifica usuário via Bearer ou IP) | PASS | `tests/infra/test_rate_limit.py -k 'ac004 or ac005'` |
| AC-002 | U-002 — limites default por rota via env (login=10, messages=20, files=10, chats=30, users=20, global=120) | PASS | `tests/infra/test_rate_limit.py -k 'ac003 or ac005'` |
| AC-003 | U-001 — 429 + `Retry-After`; endpoints abertos por IP | PASS | `tests/infra/test_rate_limit.py -k ac003` |
| AC-004 | U-004 — `RateLimiter` (janela deslizante em memória, reset) | PASS | `tests/infra/test_rate_limit.py -k ac004` |
| AC-005 | U-002 — exclui `/docs`, `/openapi.json`, `/health`; autenticados contam por usuário | PASS | `tests/infra/test_rate_limit.py -k ac005` |

## Veredito mecânico
`specs proof --strict F-016-rate-limit` → `PASS` (5/5 ACs). `uv run pytest` →
`247 passed`.

## Configuração
Variáveis (defaults): `RATE_LIMIT_LOGIN=10`, `RATE_LIMIT_CHATS=30`,
`RATE_LIMIT_MESSAGES=20`, `RATE_LIMIT_FILES=10`, `RATE_LIMIT_USERS=20`,
`RATE_LIMIT_GLOBAL=120` (req/min). Documentadas em `.env.example`.

## Arquivos
- `src/einstein_test/middleware/rate_limit.py` — `RateLimiter` +
  `RateLimitMiddleware`
- `src/einstein_test/main.py` — middleware registrado no `create_app`
- `tests/infra/test_rate_limit.py` (novo), `tests/conftest.py` (reset do
  limiter entre testes)

## Correções do deep review
- **`POST /chats` agora é limitado** (`RATE_LIMIT_CHATS`) — `_route_for`
  mapeava `/chats` como `None` (limite morto); teste com 4º create → 429.
- **XFF confiável só via proxy**: `X-Forwarded-For` é ignorado a menos que o
  peer direto esteja em `TRUSTED_PROXIES` (usa a entrada mais à direita);
  teste confirma que spoofing não burla o login (IP real).
- **Memory-DoS mitigado**: `MAX_KEYS` limita o número de chaves do rate
  limiter; `RateLimiter.allow` é atômico via `threading.Lock`.
- `_env_int` clamp ≥ 1 (evita 500 vs 429 com env 0/negativo); `reset()`
  minúsculo; fixture `_reset` duplicada e `_make_env` morto removidos.

## Notas
- Contador em memória (single-process/woker; escala ~50). Para
  multi-processo/Redis, o backend seria trocado (mantendo a interface).
- Rotas globais (`GET /chats/{id}` etc.) contam apenas no limite global por
  usuário; os limites específicos se aplicam aos `POST` sensíveis.