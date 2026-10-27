# F-014 — Pool de conexões do Postgres (concorrência)

## O que foi feito
O engine do SQLAlchemy agora tem **pool de conexões configurável** via env com
defaults adequados para a concorrência alvo (~50 usuários), e a criação do
engine foi **centralizada** numa factory única.

- Defaults: `pool_size=10`, `max_overflow=20` (total até 30 conexões),
  `pool_timeout=30s`, `pool_pre_ping=True`.
- Env vars: `DATABASE_POOL_SIZE`, `DATABASE_MAX_OVERFLOW`,
  `DATABASE_POOL_TIMEOUT` (documentadas no `.env.example`).
- `create_engine_from_config(url=None)` é a factory única; `get_session` e
  `configure_session_factory` a usam (o engine não é criado inline no
  get_session). Em SQLite (testes), os parâmetros de pool são omitidos porque
  o dialect não os suporta (SingletonThreadPool/StaticPool).

## Critérios de aceite implementados

| AC | História | Status | Prova |
|----|----------|--------|-------|
| AC-001 | U-001 — `create_engine_from_config` com pool_size/max_overflow/pool_timeout/pool_pre_ping; get_session usa a factory | PASS | `tests/infra/test_pool.py -k ac001` |
| AC-002 | U-002 — `configure_session_factory` aceita engine ou url; criação centralizada | PASS | `tests/infra/test_pool.py -k ac002` |
| AC-003 | U-003 — pool_pre_ping + pool_timeout; documentado no `.env.example` | PASS | `tests/infra/test_pool.py -k ac003` |
| AC-004 | U-004 — teste da factory (params do QueuePool) + 20 sessões paralelas (threads) | PASS | `tests/infra/test_pool.py -k ac004` |

## Veredito mecânico
`specs proof --strict F-014-pool` → `PASS` (4/4 ACs). `uv run pytest` →
`217 passed`.

## Correções do deep review
- Teste de pool usa **valores de env distintos dos defaults** (3/7/5) para
  provar override; `test_ac003` agora verifica `pool._pre_ping is True` e
  `pool._timeout`.
- Concorrência (AC-004) roda contra **SQLite em arquivo com QueuePool
  compartilhado** (não SingletonThreadPool por-thread), exercitando o pool.
- `"sqlite" in url` substituído por `make_url(url).get_backend_name()`.
- `create_engine_from_config` valida/clampa valores (não quebra com env ruim);
  lazy init de `_SessionLocal` protegido por `threading.Lock`;
  `configure_session_factory(Engine|str)`; caminho lazy de `get_session` com
  `DATABASE_URL` testado.

## Arquivos
- `src/einstein_test/api/dependencies.py` — `create_engine_from_config` +
  `get_session`/`configure_session_factory` usando a factory
- `.env.example` — variáveis do pool
- `tests/infra/test_pool.py` (novo)

## Notas
- Total de conexões = `pool_size + max_overflow` = 30, abaixo do
  `max_connections=100` do postgres do compose.
- O teste de concorrência abre 20 sessões em threads paralelas executando
  `SELECT` no SQLite; o teste dos parâmetros usa url postgres e inspeciona o
  `QueuePool` (sem conectar).