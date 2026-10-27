# F-016 — Rate limiting (global e por endpoint)

## Resumo
Um **middleware** global de rate limiting por **usuário** (autenticado) ou **IP**
(anônimo) é aplicado aos endpoints sensíveis (SSE, upload, login) com limites
default por endpoint, contados **em memória** (single process/woker, escala ~50).
Resposta `429 Too Many Requests` quando excedido. Configurável via env.

## Histórias de usuário
- U-001 — **Como** usuário, **quero** que o servidor limite requisições
  excessivas (SSE/upload/login), **para** não prejudicar os demais nem gerar
  custo de tokens/CPU descontrolado.
- U-002 — **Como** dev, **quero** um middleware global reutilizável (por
  usuário/IP) com limites configuráveis por endpoint, **para** proteger sem
  duplicar lógica.
- U-003 — **Como** dev, **quero** resposta `429` com cabeçalho `Retry-After`,
  **para** clientes saberem quando tentar de novo.
- U-004 — **Como** dev, **quero** que o contador seja em memória (dict com
  janela deslizante) e zerável, **para** operar single-process sem Redis e
  permitir testes determinísticos.

## Critérios de aceite
> Critérios são registrados mecanicamente (AC-### → story → semântica técnica → dono T-###)
> — edite `criteria.reg` e reflita aqui por legibilidade ponto a ponto.

- AC-001 — [U-002] Middleware de rate limiting (`RateLimitMiddleware`) aplicado
  no app; identifica o usuário autenticado via `Authorization` (email) ou IP do
  cliente (X-Forwarded-For/remote).
- AC-002 — [U-002] Limites default por caminho (configuráveis via env):
  `POST /auth/login`=10/min, `POST /chats/*/messages`=20/min,
  `POST /chats/*/files`=10/min, demais protegidos=120/min global por usuário.
- AC-003 — [U-001/U-003] Ao exceder o limite → **429** com `Retry-After` (em
  segundos) e mensagem clara; endpoints abertos (ex.: `/users`) também podem
  ser limitados por IP.
- AC-004 — [U-004] Contador em memória (janela deslizante por chave
  `usuário|rota`), com `reset` em testes; sem dependência nova além de `time`.
- AC-005 — [U-002] O middleware NÃO limita `/docs`, `/openapi.json`, `/health`
  (se existir) e não quebra os fluxos normais de auth (requests autenticados
  contam por usuário, não por IP).

## Suposições (status: aberto|confirmada|rejeitada)
- A-001 — Middleware global por usuário/IP, sem lib externa (slowapi). — confirmada
- A-002 — Limites default por endpoint via env (login=10, messages=20, files=10, global=120). — confirmada
- A-003 — Contador em memória (dict com janela deslizante). — confirmada
- A-004 — Resposta 429 com Retry-After. — confirmada

## Perguntas em aberto
- (nenhuma)