# F-020 — Retry no processamento de arquivos (Celery)

## Resumo
A task `vectorize_file` hoje marca `error` na primeira falha qualquer —
incluindo falhas **transientes** (conexão/storage/LLM timeout, 5xx) que poderiam
ter sucesso num retry. Esta feature adiciona **autoretry do Celery com backoff
exponencial** (default `max_retries=3`, `retry_backoff`), preservando
idempotência (arquivo `ready` não é reprocessado) e antes capturando erros
**permanentes** (url inválida, arquivo ausente, invariants) que **não** devem
retry. `error_detail` reflete a última tentativa.

## Histórias de usuário
- U-001 — **Como** dev, **quero** que falhas transientes na vetorização
  sejam tentadas novamente com backoff, **para** o processamento ser resiliente
  a picos do storage/LLM.
- U-002 — **Como** dev, **quero** que erros permanentes (url inválida, invariants)
  NÃO sejam re-tentados, **para** não gastar tentativas inúteis.
- U-003 — **Como** dev, **quero** idempotência preservada (arquivo `ready` não é
  reprocessado), **para** não duplicar chunks em redelivery.
- U-004 — **Como** dev, **quero** que `error_detail` registre a última causa após
  esgotar as tentativas, **para** diagnóstico no `GET /files/{id}`.

## Critérios de aceite
> Critérios são registrados mecanicamente (AC-### → story → semântica técnica → dono T-###)
> — edite `criteria.reg` e reflita aqui por legibilidade ponto a ponto.

- AC-001 — [U-001] `vectorize_file` ganha `autoretry_for` das exceções
  transientes (ConnectionError, timeout, 5xx/transient do storage/LLM),
  `retry_backoff=True`, `retry_backoff_max`, `max_retries` (env
  `VECTORIZE_MAX_RETRIES`, default 3) e `retry_jitter`.
- AC-002 — [U-002] Erros permanentes (`VectorizationError`, url inválida,
  arquivo não encontrado) **não** disparam retry — marcam `error` na primeira
  tentativa.
- AC-003 — [U-003] Idempotência mantida: se `status == ready`, retorna sem
  reprocessar (guard existente preservado).
- AC-004 — [U-004] Após esgotar `max_retries`, `status=error` com `error_detail`
  (nome da exceção da última tentativa); a task é marcada `failed` no resultado
  Celery apenas quando esgotou retries.

## Suposições (status: aberto|confirmada|rejeitada)
- A-001 — Celery `autoretry_for` com backoff exponencial (max_retries=3 default). — confirmada
- A-002 — Erros permanentes não retry (marcam error). — confirmada
- A-003 — Idempotência preservada (ready → skip). — confirmada
- A-004 — `error_detail` = última causa após esgotar. — confirmada

## Perguntas em aberto
- (nenhuma)