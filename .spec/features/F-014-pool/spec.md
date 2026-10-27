# F-014 — Pool de conexões do Postgres (concorrência)

## Resumo
O engine do SQLAlchemy hoje usa o pool **default** (SQLAlchemy `QueuePool`:
`pool_size=5`, `max_overflow=10`), insuficiente para a concorrência alvo
(~50 usuários). Esta feature configura o pool explicitamente via env vars com
defaults, adiciona `pool_timeout`/`pool_pre_ping`, centraliza a criação do
engine (factory única) e prova a concorrência com teste de N sessões paralelas.

## Histórias de usuário
- U-001 — **Como** dev, **quero** configurar `pool_size`/`max_overflow` do
  engine via env (defaults 10/20), **para** suportar ~50 requests simultâneos
  sem esgotar conexões.
- U-002 — **Como** dev, **quero** que o engine seja criado por uma factory
  única (`create_engine_from_config`) reutilizada por
  `get_session`/`configure_session_factory`, **para** não duplicar a lógica de
  pool.
- U-003 — **Como** dev, **quero** `pool_pre_ping` e `pool_timeout`
  configurados, **para** conexões recicladas não falharem e não haver espera
  infinita.
- U-004 — **Como** dev, **quero** um teste que cria N sessões paralelas
  (threads) executando queries, **para** provar que o pool suporta
  concorrência sem quebrar.

## Critérios de aceite
> Critérios são registrados mecanicamente (AC-### → story → semântica técnica → dono T-###)
> — edite `criteria.reg` e reflita aqui por legibilidade ponto a ponto.

- AC-001 — [U-001] `create_engine_from_config(url=None) -> Engine` com
  `pool_size=env.DATABASE_POOL_SIZE (10)`, `max_overflow=env.DATABASE_MAX_OVERFLOW
  (20)`, `pool_timeout=env.DATABASE_POOL_TIMEOUT (30)`, `pool_pre_ping=True`;
  `get_session` passa a usar essa factory.
- AC-002 — [U-002] `configure_session_factory` aceita engine ou url; a criação
  do engine fica na factory única; `get_session` não cria engine inline.
- AC-003 — [U-003] `pool_pre_ping=True` e `pool_timeout` definidos no engine;
  documentado em `.env.example`.
- AC-004 — [U-004] Teste: factory cria engine com parâmetros de pool corretos
  (inspeciona `engine.pool.size()`/`max_overflow`); teste de concorrência com
  N=20 sessões paralelas (threads) executando `select 1`/query simples sem
  erro.

## Suposições (status: aberto|confirmada|rejeitada)
- A-001 — pool_size=10, max_overflow=20, pool_timeout=30, pool_pre_ping=True. — confirmada
- A-002 — Config via env vars com defaults (`DATABASE_POOL_SIZE`,
  `DATABASE_MAX_OVERFLOW`, `DATABASE_POOL_TIMEOUT`). — confirmada
- A-003 — Factory única `create_engine_from_config` reutilizada por
  get_session/configure_session_factory. — confirmada
- A-004 — Teste de concorrência com N=20 sessões paralelas. — confirmada

## Perguntas em aberto
- (nenhuma)