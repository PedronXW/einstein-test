# F-029 — Multi-worker + rate limit com Redis

## O que foi feito
Escala horizontal da API e rate limit compartilhado:

- **`main.main()`** agora aceita `--workers N` (argparse) e sobe o uvicorn com
  `workers=N` usando a **factory como string** (`einstein_test.main:create_app`,
  exigido pelo uvicorn para multi-processo). `reload` é desativado quando
  `workers > 1` (incompatível). Confirmado: `uv run einstein-test --workers 2`
  sobe 2 processos.
- **Rate limit com backend Redis** (`RATE_LIMIT_BACKEND=redis`): `RateLimiter`
  usa `INCR`+`EXPIRE` (janela fixa) numa chave `rl:{identidade}:{rota}` —
  contagem **compartilhada entre workers** (limite efetivo não vira ×N). Sem
  Redis acessível, **cai para memória** (não quebra). Default continua
  `memory`.
- **Compose**: serviço `api` usa `--workers $API_WORKERS` (env, default 1) e
  `RATE_LIMIT_BACKEND` (default memory) — documentado para produção com Redis.

## Critérios de aceite implementados

| AC | História | Status | Prova |
|----|----------|--------|-------|
| AC-001 | U-001 — `main.main` com `--workers` + factory-string; reload off se workers>1 | PASS | `tests/infra/test_multiprocess.py -k ac001` |
| AC-002 | U-001 — compose api com `--workers`/`API_WORKERS` | PASS | `tests/infra/test_multiprocess.py -k ac002` |
| AC-003 | U-002 — `RateLimiter` backend Redis (INCR/EXPIRE) com fallback memória | PASS | `tests/infra/test_multiprocess.py -k ac003` |
| AC-004 | U-003 — middleware usa `RATE_LIMIT_BACKEND`; chave `rl:{identidade}:{rota}` | PASS | `tests/infra/test_multiprocess.py -k ac004` |
| AC-005 | U-004 — memória default; redis com skip/fallback; suíte + CLI verificados | PASS | `tests/infra/test_multiprocess.py -k ac005` |

## Veredito mecânico
`specs proof --strict F-029-multi-worker` → `PASS` (5/5 ACs). `uv run pytest` →
`331 passed, 1 deselected`. `ruff check .` → all passed.

## Como usar
```bash
# 1 worker (default) — reload
uv run einstein-test

# N workers (multi-processo) com rate limit compartilhado
RATE_LIMIT_BACKEND=redis uv run einstein-test --workers 4

# Compose (produção): API_WORKERS+N + RATE_LIMIT_BACKEND=redis
API_WORKERS=4 RATE_LIMIT_BACKEND=redis docker compose up --build api
```

## Arquivos
- `src/einstein_test/main.py` (argparse `--workers`/`--reload`)
- `src/einstein_test/middleware/rate_limit.py` (`RATE_LIMIT_BACKEND`,
  `RateLimiter` com backend redis/memory, `_redis_key`)
- `docker-compose.yml` (api com `--workers` + `API_WORKERS`/`RATE_LIMIT_BACKEND`)
- `tests/infra/test_multiprocess.py` (novo)

## Notas
- Com `RATE_LIMIT_BACKEND=redis`, o rate limit é compartilhado entre workers —
  o limite do `.env` vale para a API inteira (não multiplicado por worker).
- Redis indisponível → fallback imediato para memória (fail-open leve no meio
  do request). Iniciar com `redis` exige o serviço de pé.
- O `--reload` fica implícito (default) só com 1 worker; para dev mantém
  `einstein-test --reload`.