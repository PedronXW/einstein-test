# F-019 — Logs robustos (JSON estruturado + request_id)

## Resumo
Configuração central de logging em **JSON estruturado** (linhas parseáveis),
inclusão de **request_id** por request HTTP (propagado a todos os logs daquele
request), **access log** via middleware (status, latência, user_id, IP) e
substituição dos `logger.*` soltos por logs estruturados nos pontos críticos
(upload enqueue, RAG/SSE, task Celery). `request_id` também é retornado no
header `X-Request-Id`. Política de privacidade: **nunca logar conteúdo de
prompt/arquivos** — apenas ids e contagens.

## Histórias de usuário
- U-001 — **Como** dev, **quero** logs em JSON estruturado com `request_id` no
  STDOUT (app + worker), **para** correlacionar operações e monitorar.
- U-002 — **Como** dev, **quero** um middleware que gera `request_id` por
  request e faz **access log** (method, path, status, latency_ms, user_id, ip),
  **para** observar latência/erros por endpoint.
- U-003 — **Como** dev, **quero** logs estruturados nos pontos críticos (upload,
  RAG, task) sem vazar conteúdo de prompt/arquivos, **para** depuração segura.
- U-004 — **Como** dev, **quero** configurar `configure_logging()` reutilizável
  (app e worker) com `LOG_LEVEL` via env, **para** nível ajustável.

## Critérios de aceite
> Critérios são registrados mecanicamente (AC-### → story → semântica técnica → dono T-###)
> — edite `criteria.reg` e reflita aqui por legibilidade ponto a ponto.

- AC-001 — [U-001/U-004] `logging_setup.configure_logging()` aplica JSON
  formatter (ts, level, logger, msg, request_id) ao root + loggers da app;
  STDOUT; `LOG_LEVEL` default INFO; chamado no entrypoint do app e do worker.
- AC-002 — [U-002] `RequestIdMiddleware` gera `request_id` (UUID) por request,
  injeta `X-Request-Id` na resposta e faz access log estruturado ao final
  (method, path, status, latency_ms, user_id, ip). Registrado no `create_app`
  antes do rate limit.
- AC-003 — [U-002] Logs do mesmo request dentro dos services/endpoints
  carregam o `request_id` (logging.Filter + contextvar).
- AC-004 — [U-003] Logs estruturados em `enqueue_vectorization` (file_id,
  status), `messages.py` RAG (chat_id, n_tokens, error) e `tasks/vectorize_file`
  (attempt, status) — com `request_id`/ids, **sem** conteúdo de prompt/arquivo.
- AC-005 — [U-001] Testes: JSON parseável no handler; middleware propaga
  `X-Request-Id` e access log contém request_id/status/latency; logs do RAG não
  contêm o texto da pergunta nem chunks; ENV prefixos; `get_logger` retorna
  logger funcional.

## Suposições (status: aberto|confirmada|rejeitada)
- A-001 — Logs JSON estruturado no STDOUT (parsáveis), `LOG_LEVEL` via env. — confirmada
- A-002 — Middleware RequestID + access log + header `X-Request-Id`. — confirmada
- A-003 — request_id propagado via logging.Filter + contextvar. — confirmada
- A-004 — Nunca logar conteúdo de prompt/arquivos (só ids/contagens). — confirmada

## Perguntas em aberto
- (nenhuma)