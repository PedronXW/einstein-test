# F-029 — Multi-worker + rate limit com Redis

## Resumo
Hoje o rate limiter é em **memória** (F-016), contando por processo — com
`--workers N` (multi-processo), cada worker teria contagem própria (limite
efetivo ×N), e o singleton do RAG/threadpool também seria por processo. Esta
feature:

- **Rate limit com backend Redis** (contagem compartilhada entre workers),
  mantendo fallback em memória quando Redis indisponível/`RATE_LIMIT_BACKEND=memory`.
- **Entrypoint/CLI** aceita `--workers` (com a string da factory — necessária
  para workers) e o compose expõe `api` com `command` que usa `--workers`.

O objetivo é escala horizontal: iniciar N workers que compartilham a contagem
de rate limit via Redis.

## Histórias de usuário
- U-001 — **Como** dev/operador, **quero** iniciar a API com vários workers
  (`--workers N`), **para** aproveitar múltiplos cores e mais requests
  simultâneos.
- U-002 — **Como** dev/operador, **quero** que o rate limit seja **compartilhado**
  entre workers (via Redis), **para** que o limite não seja multiplicado por
  worker.
- U-003 — **Como** operador, **quero** que o compose use workers na API,
  **para** produção com mais capacidade.
- U-004 — **Como** dev, **quero** que sem Redis/config o rate limit caia para
  memória (fallback), **para** não quebrar o ambiente local/testes.

## Critérios de aceite
> Critérios são registrados mecanicamente (AC-### → story → semântica técnica → dono T-###)
> — edite `criteria.reg` e reflita aqui por legibilidade ponto a ponto.

- AC-001 — [U-001] `main.main()` passa a aceitar `--workers` (argparse) e usa
  `uvicorn(..., workers=N)` — com a factory como **string** `"einstein_test.main:create_app"`
  (necessário para `workers`); default 1 (reload=false se workers>1).
- AC-002 — [U-001] Compose serviço `api` usa `command` com a factory-string +
  `--workers` (env `API_WORKERS`, default 1).
- AC-003 — [U-002] `RateLimiter` ganha backend opcional **Redis**
  (`RATE_LIMIT_BACKEND=redis`, usa `redis.Redis` com INCR+EXPIRE ou janela
  fixa); falha/skip se Redis indisponível e cai para memória.
- AC-004 — [U-003] `RateLimitMiddleware` usa o backend escolhido
  (`RATE_LIMIT_BACKEND` env: `memory`|`redis`, default memory); com redis, a
  chave do contador é `rl:{identidade}:{rota}` (janela fixa 60s).
- AC-005 — [U-004] Tests: memória continua (default); redis é testado com
  contador mock/skip; a suíte completa e o CLI `--workers` são verificados
  (worker real opcional, verificação estrutural).

## Suposições (status: aberto|confirmada|rejeitada)
- A-001 — CLI `--workers` com factory-string; compose api usa workers. — confirmada
- A-002 — Rate limit Redis (janela fixa INCR/EXPIRE) com fallback memória. — confirmada
- A-003 — `RATE_LIMIT_BACKEND` env (memory|redis). — confirmada
- A-004 — Escala horizontal mantém o limite efetivo (não ×N). — confirmada

## Perguntas em aberto
- (nenhuma)